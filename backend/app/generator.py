import re
import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_cohere import ChatCohere, CohereEmbeddings
from .config import settings
from langchain_core.messages import HumanMessage, AIMessage
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


def generate_manim_code(prompt: str) -> str:
    """Generate Manim code using Cohere model with improved retrieval context."""
    add_message_to_history(HumanMessage(content=prompt))

    query_enhancement_prompt = """
        You are a Manim Library Search Optimizer. Your task is to translate a user's natural language request into a precise search query for the Manim documentation and API reference.

        Original request: {input}

        Construct a search query by following these steps:

        1. **Map to API Primitives:** specific Manim classes needed to build the visual.
        - Example: "Draw a box" -> `Rectangle`, `Square`, `SurroundingRectangle`
        - Example: "Show an equation" -> `MathTex`, `LaTeX`
        - Example: "Slide text in" -> `FadeIn`, `Write`, `Shift`

        2. **Deconstruct High-Level Concepts:** If the user asks for a complex diagram (e.g., "Neural Network", "Solar System"), list the building blocks.
        - "Neural Network" -> `Circle`, `Line`, `VGroup`, `Graph`
        - "Solar System" -> `Sphere`, `Orbit`, `Rotate`, `ThreeDScene`

        3. **Include Layout & Grouping Terms:** If the request implies structure or ordering, include positioning keywords.
        - Keywords: `VGroup`, `arrange`, `next_to`, `align_to`, `grid`

        4. **Identify Mathematical Domain:** If a specific math field is mentioned, include the relevant module.
        - Example: `manim.mobject.graphing`, `manim.mobject.three_d`, `manim.scene.vector_space_scene`

        Output ONLY a comma-separated list of the top 5-10 most relevant search terms.

Enhanced search query:"""

    try:
        enhanced_query_response = chat.invoke(
            input=query_enhancement_prompt.format(input=prompt)
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

        system_prompt = """
        You are an elite Manim Animation Expert. Your goal is to write Python code using the Manim library to visualize complex concepts for educational videos.

        ### 1. CODE STRUCTURE & FORMAT
        - **Imports:** Always start with `from manim import *` and `import numpy as np`.
        - **Class Structure:** Define a class inheriting from `Scene` (e.g., `class ConceptVisual(Scene):`).
        - **Method:** Write all logic inside the `construct(self):` method.
        - **Output:** Return ONLY the raw Python code. Do not wrap it in markdown ticks (```python) or add text explanations outside the code.

        ### 2. VOICEOVER SYNCHRONIZATION (CRITICAL)
        - **Pacing:** You are creating a video that will be narrated.
        - **The Rule:** After *every* major step (creating a shape, writing text, moving an object), you MUST insert `self.wait(2)` or `self.wait(3)`.
        - **Reasoning:** This silence allows the AI narrator time to explain what just appeared on screen.

        ### 3. LAYOUT & SPATIAL AWARENESS
        - **Screen Limits:** Canvas is **14 units wide** x **8 units high**.
        - **Object Sizing:** Never create objects wider than 3 units unless they are the background.
        - **Text Sizing:** Use `font_size=24` for labels, `font_size=36` for titles, `font_size=18` for secondary data.
        - **Container Style:** All Rectangles/Circles used as containers must have `fill_color=BLACK` and `fill_opacity=1`.
        - **Labeling Strategy:**
            - Primary labels go OUTSIDE the container: `.next_to(box, UP)`.
            - **STACKING RULE:** If multiple text objects belong above/below the same container, stack them relative to *each other*, not the container.
            *WRONG:* `text1.next_to(box, UP)`, `text2.next_to(box, UP)` (Causes overlap)
            *CORRECT:* `text1.next_to(box, UP)`, `text2.next_to(text1, UP)` (Stacks them cleanly)

        #### 3.1 SEQUENTIAL FLOW (CRITICAL)
        - When visualizing a process (Step A -> Step B):
        - **NEVER** place Step B on top of Step A using `.move_to(step_a.get_center())`.
        - **ALWAYS** place Step B next to Step A using `.next_to(step_a, RIGHT, buff=1.5)`.
        - Use `VGroup` to group a Box+Label before positioning the group.

        ### 4. CRITICAL SYNTAX RULES (DO NOT BREAK)
        - **Rule A (Arrows):** `GrowArrow` requires an **Mobject**, not coordinates.
            - *WRONG:* `self.play(GrowArrow(start, end))`
            - *CORRECT:* `self.play(GrowArrow(Arrow(start, end)))`
        - **Rule B (Edges):** Connect arrows to **Edges**, not Centers.
            - *WRONG:* `Arrow(box.get_center(), ...)`
            - *CORRECT:* `Arrow(box.get_right(), ...)` or `Arrow(box.get_edge_center(UP), ...)`
        - **Rule C (Transform):** `Transform` requires two Mobjects. Never transform a string.
            - *WRONG:* `Transform(text_obj, "New String")`
            - *CORRECT:* `Transform(text_obj, Text("New String"))`
        - **Rule D (2D vs 3D):** Use `Rectangle`/`Circle` (2D) instead of `Cylinder`/`Cube` (3D).
        - **Rule E (Path Animations):** `MoveAlongPath` requires a **Physical Path** (Line/Arc/Circle).
            - *WRONG:* `MoveAlongPath(obj.animate.move_to(...))`  <-- CAUSES CRASH
            - *CORRECT:* `MoveAlongPath(obj, Line(start, end))` or `MoveAlongPath(obj, ArcBetweenPoints(start, end))`

        ### 5. REFERENCE EXAMPLE (STACKED LABELS & FLOW)
        ```python
        from manim import *
        class StackedFlow(Scene):
            def construct(self):
                # 1. Input
                box1 = Rectangle(width=2, height=1, fill_color=BLACK, fill_opacity=1)
                # Primary Label relative to Box
                label1_main = Text("Main Title", font_size=24).next_to(box1, UP)
                # Secondary data STACKED relative to Main Label
                label1_data = Text("(Data: [1,2,3])", font_size=18, color=YELLOW).next_to(label1_main, UP, buff=0.1)
                step1 = VGroup(box1, label1_main, label1_data).to_edge(LEFT)
                self.play(Create(step1))
                self.wait(2)

                # 2. Process (Placed to right)
                box2 = Rectangle(width=2, height=1, fill_color=BLACK, fill_opacity=1)
                label2 = Text("Process", font_size=24).next_to(box2, UP)
                step2 = VGroup(box2, label2).next_to(step1, RIGHT, buff=2)
                
                # 3. Connect
                self.play(GrowArrow(Arrow(box1.get_right(), box2.get_left())))
                self.play(Create(step2))
                self.wait(3)
        Generate Python code for the user's request following these strict guidelines. """

        human_prompt = (
            "Concept to visualize: {input}\n\nPlease provide only the Python code."
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(human_prompt),
            ]
        )

        chat_prompt_value = chat_prompt.format_prompt(
            input=prompt, context=context_text
        )

        response = chat.invoke(
            input=chat_prompt_value.to_messages(),
        )

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
