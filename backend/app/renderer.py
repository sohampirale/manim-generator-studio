import os
import logging
import subprocess
import tempfile
import glob
import shutil
from .config import settings
from .generator import generate_manim_code
from .supabase_client import update_job_data, upload_to_supabase
from langchain_core.messages import HumanMessage, AIMessage,SystemMessage
from langchain_cohere import ChatCohere
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import re
import json
import math
from cartesia import Cartesia,AsyncCartesia
import asyncio
from pydantic import BaseModel, Field

# Define the data structure you want the LLM to return
class manim_synchronized_transcript(BaseModel):
    """The complete plan for generating a Manim video."""
    
    manim_synchronized_transcript: list[any] = Field(
        description="Array of objects of manim_synchronized_transcript with each obj having 3 properties pahse_id, voiceover_text, visual_instruction"
    )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RENDER_DIR = settings.RENDER_DIR
MAX_ITERATIONS = 5

chat = ChatCohere(
    model="command-r-plus-08-2024", 
    verbose=True,
    cohere_api_key=settings.COHERE_API_KEY,
    temperature=0.3 
)

llm_with_structured_output = chat.with_structured_output(manim_synchronized_transcript)

def run_manim(code: str, temp_dir: str, quality: str = "m") -> tuple[bool, str]:
    """
    Run Manim code and render the animation in a temporary directory.

    Args:
        code: The Python code to render
        temp_dir: Directory to save the rendered video temporarily
        quality: Render quality (l=low, m=medium, h=high)

    Returns:
        Tuple of (success, error_message or output_file)
    """

    temp_path = None
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Using temporary directory: {temp_dir}")

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py", mode="w", delete=False
            ) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name
                logger.info(f"Created temporary file: {temp_path}")
        except Exception as e:
            logger.error(f"Failed to create temporary file: {str(e)}")
            return False, f"Failed to create temporary file: {str(e)}"

        cmd = [
            "python",
            "-m",
            "manim",
            temp_path,
            "Scene",
            f"-q{quality}",
            "--format=mp4",
            f"--media_dir={temp_dir}",
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        try:
            process = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=settings.MANIM_TIMEOUT
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Manim rendering timed out after {settings.MANIM_TIMEOUT} seconds")
            return False, f"Rendering timed out after {settings.MANIM_TIMEOUT} seconds"

        logger.info(f"Manim stdout: {process.stdout}")
        logger.error(f"Manim stderr: {process.stderr}")

        if process.returncode != 0:
            logger.error(f"Manim rendering failed with exit code {process.returncode}")
            return False, process.stderr

        mp4_files = [
            f
            for f in glob.glob(os.path.join(temp_dir, "**", "*.mp4"), recursive=True)
            if "partial_movie_files" not in f
        ]
        logger.info(f"Found MP4 files: {mp4_files}")

        if not mp4_files:
            logger.error("No MP4 file found after rendering")
            return False, "No MP4 file found after rendering"

        output_file = mp4_files[0]

        logger.info(f"Manim rendering completed successfully: {output_file}")
        return True, output_file

    except Exception as e:
        error_msg = f"Error running Manim: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Removed temporary file: {temp_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up temporary file {temp_path}: {str(e)}"
                )

def normalize_word(text):
    """
    Removes punctuation and converts to lowercase for easy matching.
    Example: "Let's!" -> "lets"
    """
    return re.sub(r'[^\w]', '', text).lower()

def map_timestamps_to_phases(phases_json, cartesia_timestamps):
    """
    Inputs:
        phases_json: List of dicts (from your LLM Step 2)
        cartesia_timestamps: List of dicts [{'word': 'Hello', 'start': 0.1, 'end': 0.3}, ...]
    
    Returns:
        The phases_json with a new 'audio_duration' key in each object.
    """
    
    current_ts_index = 0
    total_timestamps = len(cartesia_timestamps)

    for phase in phases_json:
        text = phase.get('voiceover_text', "")
        
        # 1. Clean the text into a list of checkable words
        # "Let's start." -> ["lets", "start"]
        target_words = [normalize_word(w) for w in text.split()]
        
        # Filter out empty strings
        target_words = [w for w in target_words if w]

        if not target_words:
            # If phase has no text (just silence), default to 2s or 0s
            phase['audio_duration'] = 2.0
            continue

        # 2. Capture Start Time
        # The start of this phase is the start time of the next available word in the stream
        if current_ts_index < total_timestamps:
            start_time = cartesia_timestamps[current_ts_index]['start']
        else:
            phase['audio_duration'] = 2.0
            continue

        # 3. Advance the cursor through the timestamp list
        # We look for the words in this phase to "consume" them from the master list
        matches_found = 0
        
        for target_word in target_words:
            # Search forward in the timestamp list until we find a match
            # This handles cases where Cartesia might split words differently
            while current_ts_index < total_timestamps:
                ts_word = normalize_word(cartesia_timestamps[current_ts_index]['word'])
                current_ts_index += 1
                
                if ts_word == target_word: # Found a match!
                    matches_found += 1
                    break # Move to next target word
                
                # If words don't match, we skip the timestamp word (it might be a filler or noise)
        
        # 4. Capture End Time
        # The end of this phase is the 'end' time of the LAST word we consumed
        # We use (current_ts_index - 1) because the loop incremented it one extra time
        if current_ts_index > 0:
            end_time = cartesia_timestamps[current_ts_index - 1]['end']
        else:
            end_time = start_time + 2.0

        # 5. Calculate Duration & Add Buffer
        duration = end_time - start_time
        
        # CRITICAL: Add 0.5s buffer so the animation doesn't snap instantly to the next one
        phase['audio_duration'] = round(duration + 0.5, 2)

    return phases_json


async def process_rendering_job(job_id: str, prompt: str, quality: str):
    """
    Process a rendering job from start to finish with iterative error correction:
    1. Generate Manim code
    2. Run Manim to create animation in a temp directory
    3. If error occurs, try to fix up to MAX_ITERATIONS times
    4. Upload successful result to Supabase
    5. Clean up temp files
    """
    job_dir = os.path.join(RENDER_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    conversation_history = []
    conversation_history.append(HumanMessage(content=prompt))
    #prompt = user_query
    #1.create one transcript for tutoring
    #2.manim_scynchronized_transcript(generates transcript as well as mentions what the manim will be showing in the video)
    #3.TTS takes the manim_sychcronized_transcript and create one FINAL transcript with proper pauses and all and generates on entire audio
    #4.Give the manim_synchronized_transcript as well as TTS FINAL Transcript to manim code generator so it can adopt to it

    tutor_transcript_generator_system_prompt = """
    You are an expert Educational Scriptwriter for short, animated explainer videos. 
    Your task is to take a simple user topic (e.g., "Area of a Triangle") and generate a high-quality, engaging voiceover transcript.

    ### YOUR GOAL
    Write a clear, concise, and conversational script that a Text-to-Speech (TTS) engine will read. The script must explain the concept step-by-step.

    ### CRITICAL WRITING RULES:
    1.  **Pure Spoken Audio Only:** Do NOT include scene descriptions, camera directions, or visual cues like [Draw Triangle] or (Pause). Write ONLY what the voice should say.
    2.  **"Visual-Ready" Language:** Write as if the viewer is looking at the screen. Use pointing language:
        * *Good:* "Look at this shape here." / "Notice how the height connects to the base."
        * *Bad:* "Imagine a triangle." (No, we are showing it).
        * *Bad:* "I am now drawing a red line." (Don't describe the action, explain the concept).
    3.  **Pacing:** Break the text into short, logical paragraphs. Each paragraph will eventually become a distinct animation phase.
    4.  **Tone:** Enthusiastic, clear, and beginner-friendly. Avoid overly complex jargon unless you explain it.
    5.  **Length:** Keep it focused. Target a duration of 30-60 seconds (approx. 75-150 words).

    ### OUTPUT FORMAT
    Return the transcript as plain text, separated by double newlines for logical pauses.

    ### EXAMPLE INPUT:
    "Explain the Pythagorean Theorem"

    ### EXAMPLE OUTPUT:
    "Let's look at a right-angled triangle. This creates a unique relationship between its three sides.

    We call the two shorter sides 'a' and 'b', and the longest side, opposite the right angle, is the hypotenuse, 'c'.

    Now, imagine we build a square on each of these sides. The theorem tells us something fascinating about their areas.

    The area of square 'a' plus the area of square 'b' is exactly equal to the area of square 'c'. This is why we say a-squared plus b-squared equals c-squared."
    """

    messages = [
        SystemMessage(content=tutor_transcript_generator_system_prompt),
        HumanMessage(content=prompt)
    ]

    tutor_transcript = chat.invoke(messages)

    print(f'tutor_transcript : {tutor_transcript.content}')

    manim_synchronized_transcript_system_prompt = """
        You are the **Visual Director** for an automated video generation pipeline. 
        Your input is an educational voiceover transcript.
        Your output is a structured **JSON** directive that maps every chunk of audio to a specific, concrete visual instruction for a Manim animator.

        ### YOUR CORE RESPONSIBILITY
        The Manim Animator (the next agent) is a blind coder. It does not understand "show the concept." 
        You must tell it EXACTLY:
        1. **WHAT** to draw (Shape, Color, Label).
        2. **WHERE** to place it (Coordinates, Relative Position).
        3. **HOW** to move it (Animation type).

        ### CRITICAL RULES FOR VISUAL INSTRUCTIONS

        1.  **Layout & Flow (The "Anti-Overlap" Rule):**
            * Establish a visual flow (usually Left-to-Right).
            * **Explicit Positioning:** Never say "place it next to it." Say "Position this group to the RIGHT of the [Previous Object] with a buffer of 2.0 units."
            * **Memory:** Keep track of what is on screen. Do not ask to create an object that already exists. Refer to existing objects by name.

        2.  **Container Style (The "Transparency" Fix):**
            * If the visual involves a Box, Circle, or Container, explicitly instruct: "Style: Fill Color BLACK, Opacity 1.0, colored stroke."
            * This prevents lines from showing through objects.

        3.  **Labeling Strategy:**
            * Instruct the animator to place labels **OUTSIDE** objects (Above/Below), never inside, to leave room for animations.
            * If multiple labels are needed, instruct them to **STACK** (e.g., "Place label B above Label A").

        4.  **Geometry & Attachment:**
            * If attaching shapes (e.g., squares on a triangle), specify the **Exact Edge** (e.g., "Attach to the Hypotenuse/Slanted Edge", "Attach to the Bottom Edge").

        ### JSON OUTPUT FORMAT
        You must return a raw JSON list of objects. Each object represents one "Scene Phase".

        ```json
        [
        {
            "phase_id": 1,
            "voiceover_text": "Let's start with a right-angled triangle.",
            "visual_instruction": "Create a Right Triangle in the center. Labels: 'a' (bottom), 'b' (left), 'c' (hypotenuse). Style: White lines.",
            "animation_type": "Create/Write"
        },
        {
            "phase_id": 2,
            "voiceover_text": "Now, we attach a square to side 'a'.",
            "visual_instruction": "Create a Square. Position: Attached to the BOTTOM edge of the triangle. Color: Green with Black Fill. Label: 'a²' inside the square.",
            "animation_type": "GrowFromEdge"
        }
        ]```

        INPUT TRANSCRIPT:
        {transcript}

        OUTPUT:
        Generate ONLY the valid JSON list. 

    """

    messages=[
        SystemMessage(content=manim_synchronized_transcript_system_prompt),
        HumanMessage(content=f'tutor_transcript is : {tutor_transcript.content}'),
        HumanMessage(content=prompt)
    ]

    manim_synchronized_transcript = chat.invoke(messages)

    print(f'manim_synchronized_transcript : {manim_synchronized_transcript}')

    tts_final_transcript_generator_system_prompt = tts_final_transcript_generator_system_prompt = """
        You are the **Audio Mastering Agent**.
        Your ONLY goal is to output a raw string for a Text-to-Speech (TTS) engine.

        ### INPUT DATA
        You will receive a JSON list of video phases. Each phase contains:
        - `voiceover_text`: The spoken words.
        - `visual_instruction`: The context for the pause.

        ### YOUR TASK
        Convert the list into a single, continuous string with SSML break tags inserted between phrases.

        ### STRICT OUTPUT RULES
        1.  **NO MARKDOWN:** Do not wrap the output in ```xml or ```txt.
        2.  **NO JSON:** Do not output a key-value pair.
        3.  **NO CONVERSATION:** Do not say "Here is the text." Just output the text itself.
        4.  **SSML TAGS:** Use `<break time="2.0s" />` for standard pauses and `<break time="3.0s" />` for complex visual transitions.

        ### LOGIC
        1. Read Phase 1 `tutor_transcript`.
        2. Append a break tag based on Phase 1 `manin_syncrhonized_transcript` complexity.
        3. Read Phase 2 `tutor_transcript`.
        4. Append break tag...
        5. Repeat until done.

        ### EXAMPLE INTERACTION

        **Input:**
        [
        { "voiceover_text": "First, we draw a circle.", "visual_instruction": "Create Circle" },
        { "voiceover_text": "Then, we fill it with blue.", "visual_instruction": "Animate Fill" }
        ]

        **Correct Output:**
        <speak>First, we draw a circle. <break time="2.0s" /> Then, we fill it with blue. <break time="2.0s" />....<speak>
    """

    messages=[
        SystemMessage(content=tts_final_transcript_generator_system_prompt),
        HumanMessage(content=f'tutor_transcript is : {tutor_transcript.content}'),
        HumanMessage(content=f'manim_synchornized_transcript is : {manim_synchronized_transcript.content}'),
    ]

    tts_final_transcript = chat.invoke(messages)

    print(f'tts_final_transcript : {tts_final_transcript.content}')

    #
    client = AsyncCartesia(api_key=os.environ["CARTESIA_API_KEY"])

    ws = await client.tts.websocket()

    audio_chunks = []
    timestamps = []

    async for output in await ws.send(
        model_id="sonic-3",
        transcript=tts_final_transcript.content,
        voice={"mode": "id", "id": "228fca29-3a0a-435c-8728-5cb483251068"},
        output_format={"container": "raw", "encoding": "pcm_f32le", "sample_rate": 44100},
        add_timestamps=True
    ):
        if output.audio:
            audio_chunks.append(output.audio)

        # 2. Access Timestamps
        if output.word_timestamps:
            # The SDK object has lists: .words, .start, .end
            batch = output.word_timestamps
            
            # Use zip() to pair the word with its specific start/end time
            if batch.words:
                for word, start, end in zip(batch.words, batch.start, batch.end):
                    timestamps.append({
                        "word": word,
                        "start": start,
                        "end": end
                    })
                    # print(f"Synced: {word} ({start}s - {end}s)")

    print(f'timestamps : {timestamps}')
    #
    # ... inside your async function, after the loop finishes ...

    # 1. Combine all audio chunks into one binary blob
    full_audio_bytes = b"".join(audio_chunks)

    # 2. Map the timestamps to your JSON Plan
    # 'phases_json' is the list you got from the Visual Director (LLM Step 2)
    final_timed_plan = map_timestamps_to_phases(phases_json, timestamps)

    # 3. DEBUG: Print the result to see if it worked
    print("--- TIMING CALCULATED ---")
    for p in final_timed_plan:
        print(f"Phase {p['phase_id']}: {p['audio_duration']} seconds")

    # 4. Save Audio to Disk (Optional but recommended for Manim)
    # Cartesia sends raw PCM float32. You might need to convert to WAV using ffmpeg or wave
    with open("temp_voiceover.pcm", "wb") as f:
        f.write(full_audio_bytes)

    # 5. PASS TO MANIM GENERATOR
    # Now you call the LLM to write the Python code
    # The LLM will see: "audio_duration": 4.5 and write self.wait(4.5)
    manim_code = generate_manim_code(
        prompt=prompt, 
        manim_synchronized_transcript=json.dumps(final_timed_plan) # Pass the TIMED json
    )
        # # 1. Access audio using Dot Notation
        # # if output.audio:
        #     # print(f"Audio chunk: {len(output.audio)} bytes")
        #     # audio_chunks.append(output.audio)

        # # 2. Access timestamps using Dot Notation
        # # Note: The attribute is usually 'word_timestamps', not 'word'
        # if output.word_timestamps:

        #     # attributes inside might be: output.word_timestamps.words, .start, .end
        #     data = output.word_timestamps
        #     if data.words:
        #         for i, word in enumerate(data.words):
        #             start=math.floor(data.start[i])
        #             if startTime==0:
        #                 startTime=0.1
        #                 line+=" "+word
        #             elif start>startTime+3:
        #                 timestamps.append({
        #                     "line":line,
        #                     "startTime":startTime
        #                 })                    
        #                 startTime=start
        #                 line=word
        #             else:
        #                 line+=" "+word

                    # print(f"Word: '{word}' start: {data.start[i]} end: {data.end[i]}")
                    # timestamps.append({
                    #     "word": word,
                    #     "startTime": data.start[i],
                    #     "endTime": data.end[i]
                    # })
    
    #


    # client = Cartesia(api_key=settings.CARTESIA_API_KEY)

    # chunk_iter = client.tts.bytes(
    #     model_id="sonic-3",
    #     transcript=tts_final_transcript.content,
    #     voice={"mode": "id", "id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b"},
    #     output_format={"container": "wav", "sample_rate": 44100, "encoding": "pcm_f32le"}
    # )

    # with open("TTS_audio.wav", "wb") as f:
    #     for chunk in chunk_iter:
    #         f.write(chunk)

    try:
        code = generate_manim_code(prompt,manim_synchronized_transcript.content,timestamps)
        conversation_history.append(AIMessage(content=code))

        code_path = os.path.join(job_dir, "code.py")
        with open(code_path, "w") as f:
            f.write(code)

        logger.info(f"Initial code generated for job {job_id}")
    except Exception as e:
        logger.error(f"Error generating initial code for job {job_id}: {str(e)}")
        update_job_data(
            job_id=job_id,
            status="failed",
            prompt=prompt,
            message=f"Code generation failed: {str(e)}",
        )
        with open(os.path.join(job_dir, "status.txt"), "w") as f:
            f.write(f"failed\nCode generation failed: {str(e)}")
        return

    success = False
    result = ""
    final_code = code
    iteration = 0

    while not success and iteration < MAX_ITERATIONS:
        iteration += 1
        logger.info(f"Starting iteration {iteration} for job {job_id}")

        temp_iter_dir = tempfile.mkdtemp(prefix=f"manim_iter_{iteration}_")

        try:

            success, result = run_manim(str(final_code), temp_iter_dir, quality)

            if success:
                logger.info(f"Successful render on iteration {iteration}")

                final_output_dir = os.path.join(job_dir, "media")
                os.makedirs(final_output_dir, exist_ok=True)

                rel_path = (
                    os.path.relpath(result, RENDER_DIR)
                    if RENDER_DIR in result
                    else result
                )

                target_file = os.path.join(final_output_dir, os.path.basename(result))
                shutil.copy2(result, target_file)

                result = os.path.relpath(target_file, RENDER_DIR)
                break
            else:
                if iteration < MAX_ITERATIONS:
                    error_prompt = f"""
The Manim code failed to render with the following error:
```
{result}
```
Please fix the code to address this error. Only respond with the complete, corrected code - no explanations.
"""
                    conversation_history.append(HumanMessage(content=error_prompt))

                    try:
                        from .generator import generate_code_with_history

                        final_code = generate_code_with_history(conversation_history)
                        conversation_history.append(AIMessage(content=final_code))

                        with open(
                            os.path.join(job_dir, f"code_iter_{iteration}.py"), "w"
                        ) as f:
                            f.write(str(final_code))

                        with open(code_path, "w") as f:
                            f.write(str(final_code))

                        logger.info(f"Generated improved code in iteration {iteration}")
                    except Exception as e:
                        logger.error(f"Error generating improved code: {str(e)}")
                        break
        finally:
            try:
                shutil.rmtree(temp_iter_dir)
                logger.info(f"Cleaned up temporary directory: {temp_iter_dir}")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up temporary directory {temp_iter_dir}: {str(e)}"
                )

    status_path = os.path.join(job_dir, "status.txt")

    if success:
        try:
            video_full_path = os.path.join(RENDER_DIR, result)
            supabase_url = upload_to_supabase(job_id, video_full_path, final_code)

            update_job_data(
                job_id=job_id,
                status="completed",
                prompt=prompt,
                code=final_code,
                url=supabase_url,
            )

            with open(status_path, "w") as f:
                f.write("completed\n")
                if supabase_url:
                    f.write(supabase_url)
                else:
                    f.write("error_uploading")

            try:
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up local files for job {job_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up local files for job {job_id}: {str(e)}"
                )

            logger.info(
                f"Job {job_id} completed after {iteration} iterations: {supabase_url}"
            )
        except Exception as e:
            logger.error(f"Error finalizing successful job {job_id}: {str(e)}")
            with open(status_path, "w") as f:
                f.write(f"failed\nError finalizing successful job: {str(e)}")
    else:
        update_job_data(
            job_id=job_id,
            status="failed",
            prompt=prompt,
            code=final_code,
            message=f"Failed after {iteration} iterations. Last error: {result}",
        )

        with open(status_path, "w") as f:
            f.write(
                f"failed\nFailed after {iteration} iterations. Last error: {result}"
            )

        logger.info(f"Job {job_id} failed after {iteration} iterations: {result[:100]}")
