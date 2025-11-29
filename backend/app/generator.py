import re
import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_cohere import ChatCohere, CohereEmbeddings
from .config import settings
from langchain_core.messages import HumanMessage, AIMessage,SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_pinecone import PineconeVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# embedding = GoogleGenerativeAIEmbeddings(
#     model="models/embedding-001",
#     google_api_key=settings.GEMINI_API_KEY,
# )

embedding = CohereEmbeddings(
    model="embed-multilingual-v2.0",
    cohere_api_key=settings.COHERE_API_KEY
)

# chat = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     verbose=True,
#     google_api_key=settings.GEMINI_API_KEY
# )

chat = ChatCohere(
    model="command-r-plus-08-2024", 
    verbose=True,
    cohere_api_key=settings.COHERE_API_KEY,
    temperature=0.3 
)

chat_history = []

MAX_HISTORY_LENGTH = 20


def add_message_to_history(message):
    """Add a message to the global chat history and trim if needed."""
    global chat_history
    chat_history.append(message)
    if len(chat_history) > MAX_HISTORY_LENGTH:
        chat_history = chat_history[-MAX_HISTORY_LENGTH:]


def extract_python_code(text: str) -> str:
    """Extract Python code from text that might contain markdown code blocks."""
    code_pattern = re.compile(r"```(?:python)?\s*([\s\S]*?)\s*```")
    matches = code_pattern.findall(text)
    return matches[0] if matches else text


def generate_manim_code(prompt: str,manim_synchronized_transcript:str,timestamps:list) -> str:
    """Generate Manim code using Cohere model with improved retrieval context."""
    add_message_to_history(HumanMessage(content=prompt))

    query_enhancement_prompt = """
        You are a Manim Library Search Optimizer. 
        Your task is to generate a precise search query for the Manim documentation based on the User's Topic AND the specific Visual Plan.

        ### INPUTS
        1. **User Topic:** {input}
        2. **Visual Plan (JSON):** {manim_synchronized_transcript}

        ### YOUR TASK
        Construct a search query by analyzing both inputs:

        1.  **Analyze the Visual Plan:** Look at the `visual_instruction` fields in the JSON.
            * If it mentions "arrows", add `Arrow`, `GrowArrow`.
            * If it mentions "grids" or "tiles", add `VGroup`, `Square`, `arrange_in_grid`.
            * If it mentions "braces" or "labels", add `Brace`, `Text`, `next_to`.
            * If it mentions "transforming", add `ReplacementTransform`, `Transform`.

        2.  **Identify the Mathematical Domain (from User Topic):**
            * Calculus -> `Axes`, `Graph`, `TangentLine`.
            * Geometry -> `Polygon`, `Angle`, `dashed_line`.
            * Linear Algebra -> `Vector`, `Matrix`, `LinearTransformationScene`.

        3.  **Include Layout Keywords:**
            * Always include: `VGroup`, `arrange`, `next_to`, `align_to`.

        ### OUTPUT FORMAT
        Output ONLY a comma-separated list of the top 5-10 most relevant search terms. Do not add explanations.

        Enhanced search query:"""

    try:
        messages=[
            SystemMessage(content=query_enhancement_prompt),
            HumanMessage(content=f'manin_synchronized_transcript : {manim_synchronized_transcript}')
        ]

        enhanced_query_response = chat.invoke(
           messages
        )

        enhanced_query = enhanced_query_response.content
        logger.info(f"Enhanced search query: {enhanced_query}")

        doc_search = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=embedding,
            pinecone_api_key=settings.PINECONE_API_KEY,
        )

        retriever = doc_search.as_retriever()

        docs_original = retriever.invoke(prompt)

        docs_enhanced = retriever.invoke(enhanced_query)

        all_docs = docs_original + docs_enhanced
        unique_docs = []
        seen_content = set()

        for doc in all_docs:
            if doc.page_content not in seen_content:
                seen_content.add(doc.page_content)
                unique_docs.append(doc)

        doc_contents = []
        for doc in unique_docs[:7]:
            doc_contents.append(doc.page_content)

        context_text = "\n\n---\n\n".join(doc_contents)

        logger.info(f"Retrieved {len(unique_docs)} unique relevant documents")

        manim_code_generator_system_prompt = """
            You are an elite Manim Python Developer. 
            Your goal is to convert a structured JSON `scene_plan` into a fully functional, crash-free `Scene` class.

            ### INPUT DATA
            You will receive a JSON list called `scene_plan`. Each item represents a phase of the video:
            - `visual_instruction`: The specific shape, text, or diagram to draw.
            - `animation_type`: The suggested Manim animation class (e.g., Create, Write, Transform, Flash).

            ### CORE RESPONSIBILITIES
            1.  **Iterate:** Write code for Phase 1, then Phase 2, etc., following the JSON order.
            2.  **Timing:** At the end of *every* phase, insert `self.wait(2)` (or `self.wait(3)` for complex animations).
            3.  **Variable Management:** Give variables descriptive names (e.g., `triangle`, `label_a`). Use `VGroup` to group related items (e.g., `box_group = VGroup(box, label)`).

            ### VISUAL STYLE & LAYOUT RULES (CRITICAL)
            1.  **Container Style (The "Ghost" Fix):** - All `Rectangle`, `Circle`, `Square` acting as containers must have `fill_color=BLACK`, `fill_opacity=1`, and a colored `stroke_color`.
                - This prevents arrows from showing through them.
            2.  **Labeling (The "Collision" Fix):** - Place labels **OUTSIDE** shapes (e.g., `.next_to(box, UP)`).
                - **STACKING:** If adding a second label (like a data value) above a box that already has a title, stack it relative to the **TITLE**, not the box.
                - *Example:* `val_text.next_to(title_text, UP, buff=0.2)`
            3.  **Flow & Positioning:**
                - Use Left-to-Right flow.
                - **NEVER** use `move_to(previous_obj.get_center())` for a new step (this causes overlap).
                - **ALWAYS** use `next_to(previous_group, RIGHT, buff=1.5)`.

            ### TRANSLATION LOGIC (INTERPRETING THE JSON)
            - **"Grid" or "Tiles":** Use two nested `for` loops to create small squares, add them to a `VGroup`, and arrange them.
            - **"Paintbrush" / "Fill":** Manim has no brush. Interpret this as animating the `fill_opacity` from 0 to 1 (e.g., `rect.animate.set_fill(BLUE, opacity=0.5)`).
            - **"Highlight":** Use `Indicate(mobject)` or `Circumscribe(mobject)`.
            - **"Dashed Line":** Use `DashedLine(start, end)`.

            ### SYNTAX SAFETY RAILS (DO NOT BREAK)
            1.  **Arrows:** `GrowArrow` needs an Mobject. 
                - *Correct:* `self.play(GrowArrow(Arrow(start, end)))`
            2.  **Edges:** Connect arrows to `.get_right()`, `.get_left()`, `.get_top()`, etc., NOT `.get_center()`.
            3.  **Paths:** `MoveAlongPath` needs a physical path.
                - *Correct:* `MoveAlongPath(obj, Line(start, end))`
            4.  **Transforms:** `Transform` needs two Mobjects. Convert strings to `Text()` first.

            ### OUTPUT FORMAT
            Return ONLY the raw Python code. Start with imports.

            ### SCENE PLAN (JSON):
            {manim_synchronized_transcript}

            ### CONTEXT FROM DOCS:
            {context}
            """
          
        messages=[
            SystemMessage(content=manim_code_generator_system_prompt),
            HumanMessage(content=f"manim_synchronized_transcript : {manim_synchronized_transcript}"),
            HumanMessage(content=f'user_query : {prompt}')
        ]

        response = chat.invoke(messages)

        logger.info(f"Generated response for prompt: {prompt[:30]}...")

        code = extract_python_code(response.content)
        print('-----------------------GENARATED manim code -----------------------')
        print(code)
        return code

    except Exception as e:
        logger.error(f"Error generating code: {str(e)}")
        return f"# Error generating code: {str(e)}"


def generate_code_with_history(conversation_history):
    """
    Generate improved Manim code using conversation history and error feedback.

    Args:
        conversation_history: List of HumanMessage and AIMessage instances

    Returns:
        str: Generated Python code
    """
    try:
        original_prompt = conversation_history[0].content

        doc_search = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=embedding,
            pinecone_api_key=settings.PINECONE_API_KEY,
        )

        retriever = doc_search.as_retriever()
        docs = retriever.invoke(original_prompt)

        doc_contents = [doc.page_content for doc in docs[:5]]
        context_text = "\n\n---\n\n".join(doc_contents)

        system_prompt = """
        You are an expert in debugging and fixing Manim animations. Given a conversation history that includes:
        1. The original concept request
        2. Previous code generation attempts
        3. Error messages from those attempts

        Your task is to fix the code to make it work correctly.

        Follow these rules strictly:
        1. Always include proper imports from manim.
        2. Define a construct() method that builds the visualization step by step.
        3. Use animations like Create(), Write(), etc.
        4. Keep code simple, focused, and well-commented.
        5. Do NOT include explanations or text outside Python code.
        6. Include necessary imports like numpy as np if used.
        7. ALWAYS use 'class Scene' as the class name.
        8. Carefully address the specific errors mentioned in the conversation history.

        Here's some relevant Manim documentation that might help:
        {context}

        Based on the conversation history, generate corrected Python code. Return ONLY the code, no explanations or markdown.
        """

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                MessagesPlaceholder(variable_name="history"),
            ]
        )

        chat_prompt_value = chat_prompt.format_prompt(
            context=context_text, history=conversation_history
        )

        response = chat.invoke(
            input=chat_prompt_value.to_messages(),
        )

        logger.info("Generated improved code with error context")

        code = extract_python_code(response.content)
        return code

    except Exception as e:
        logger.error(f"Error generating improved code: {str(e)}")

        last_code = None
        for msg in reversed(conversation_history):
            if isinstance(msg, AIMessage):
                last_code = msg.content
                break

        if last_code:
            return last_code
        else:
            return f"# Error generating improved code: {str(e)}"
