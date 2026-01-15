# tavus_agent.py
import logging
import os
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from pydantic import BaseModel
from livekit.agents import JobContext, RoomOutputOptions
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.plugins.turn_detector.english import EnglishModel
from livekit.plugins import silero, tavus, elevenlabs, openai

# -------------------------------------------------
# ENV
# -------------------------------------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

if "ELEVENLABS_API_KEY" in os.environ:
    os.environ["ELEVEN_API_KEY"] = os.environ["ELEVENLABS_API_KEY"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tavus-avatar")



# -------------------------------------------------
# DATA MODELS (UNCHANGED)
# -------------------------------------------------
class QuizAnswerModel(BaseModel):
    text: str
    is_correct: bool

class QuizQuestionModel(BaseModel):
    text: str
    answers: List[QuizAnswerModel]

@dataclass
class FlashCard:
    id: str
    question: str
    answer: str
    is_flipped: bool = False

@dataclass
class QuizAnswer:
    id: str
    text: str
    is_correct: bool

@dataclass
class QuizQuestion:
    id: str
    text: str
    answers: List[QuizAnswer]

@dataclass
class Quiz:
    id: str
    questions: List[QuizQuestion]

@dataclass
class UserData:
    ctx: Optional[JobContext] = None
    flash_cards: List[FlashCard] = field(default_factory=list)
    quizzes: List[Quiz] = field(default_factory=list)

    def add_flash_card(self, question: str, answer: str) -> FlashCard:
        card = FlashCard(
            id=str(uuid.uuid4()),
            question=question,
            answer=answer,
        )
        self.flash_cards.append(card)
        return card

# -------------------------------------------------
# AGENT (UNCHANGED)
# -------------------------------------------------
class AvatarAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
You are a friendly AI assistant.
Always speak English.
Keep responses short and conversational.
""",
            stt="assemblyai/universal-streaming",
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(voice_id="21m00Tcm4TlvDq8ikWAM"),
            vad=silero.VAD.load(),
        )

    @function_tool
    async def create_flash_card(
        self,
        context: RunContext[UserData],
        question: str,
        answer: str,
    ):
        userdata = context.userdata
        card = userdata.add_flash_card(question, answer)

        room = userdata.ctx.room
        participant = next(iter(room.remote_participants.values()), None)
        if not participant:
            return "Flash card created but no client found."

        payload = json.dumps({
            "action": "show",
            "id": card.id,
            "question": card.question,
            "answer": card.answer,
        })

        await room.local_participant.perform_rpc(
            destination_identity=participant.identity,
            method="client.flashcard",
            payload=payload,
        )

        return f"Flash card created: {question}"


# -------------------------------------------------
# ENTRYPOINT (UNCHANGED)
# -------------------------------------------------
async def entrypoint(ctx: JobContext):
    logger.info("Connecting to room...")
    await ctx.connect()

    agent = AvatarAgent()
    userdata = UserData(ctx=ctx)

    session = AgentSession[UserData](
        userdata=userdata,
        turn_detection=EnglishModel(),
    )

    await session.start(
        room=ctx.room,
        room_output_options=RoomOutputOptions(audio_enabled=True),
        agent=agent,
    )

    avatar = tavus.AvatarSession(
        replica_id="r68fe8906e53",
        persona_id="p2fbd605",
        api_key=os.getenv("TAVUS_API_KEY"),
    )

    logger.info("Starting Tavus avatar...")
    await avatar.start(agent_session=session, room=ctx.room)

    session.say(
        "Hello! I am your AI assistant. How can I help you today?",
        allow_interruptions=True,
    )
