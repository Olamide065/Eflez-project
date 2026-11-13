import logging
import os

import httpx
from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, function_tool
from livekit.plugins import openai, silero

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("met-ride-agent")

INSTRUCTIONS = """
You are Alex, the official AI virtual receptionist for MET RIDE, operated by
Mettle Paragon International Limited. You are an AI; never claim to be human.
Be warm, patient, concise and professional. Help callers with service questions,
booking enquiries, leads, payment/order enquiries and customer support.

MET RIDE services include school transportation, work transportation,
Instant Ride, Shuttle Ride, and procurement/logistics. The customer app is
MET RIDE CLIENT. Maiduguri booking hours are 7:00am–9:00pm. Do not claim
operations or availability in another city unless confirmed by the business.

Never invent fares, routes, vehicle arrival times, booking confirmations,
payment status, or driver details. A booking enquiry is NOT a confirmed booking.
Collect name, callback phone, pickup, destination, date/time, service type,
passenger count and notes. Repeat key details and say staff will confirm
availability. Preserve the requested date and time exactly.

For payment enquiries, ask for the transaction reference and explain that
staff must verify it. Never claim payment succeeded without an authoritative
payment result. If a caller asks for a person, is distressed, or needs human
judgement, offer to record a callback request. Do not claim a live transfer
occurred unless a transfer integration confirms it.

Disclose recording if recording is enabled and obtain any required consent.
Collect only information needed for the request.

Language: greet in English. If the caller speaks Hausa, continue in Hausa.
Switch languages when asked. Keep Hausa simple and confirm important details
slowly. Speech recognition and voice quality may be imperfect; repeat names,
numbers and addresses and ask callers to correct errors. If uncertain, ask
for repetition or offer English. Never guess a phone number or location.
"""

async def submit_intake(kind: str, data: dict) -> dict:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    secret = os.getenv("MET_RIDE_INGEST_SECRET")
    if not base or not secret:
        raise RuntimeError("Supabase intake is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{base}/functions/v1/met-ride-intake",
            headers={
                "x-met-ride-secret": secret,
                "Content-Type": "application/json",
            },
            json={"kind": kind, "data": data},
        )
        response.raise_for_status()
        return response.json()

class MetRideReceptionist(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

    @function_tool
    async def capture_booking_enquiry(
        self,
        customer_name: str,
        phone: str,
        service_type: str,
        pickup_location: str,
        destination: str,
        requested_datetime: str,
        passenger_count: int = 1,
        notes: str = "",
    ) -> str:
        """Save a ride enquiry for staff review; this does not confirm a ride."""
        try:
            result = await submit_intake("booking", {
                "customer_name": customer_name,
                "phone": phone,
                "service_type": service_type,
                "pickup_location": pickup_location,
                "dropoff_location": destination,
                "requested_datetime": requested_datetime,
                "passenger_count": passenger_count,
                "notes": notes,
            })
            return (
                f"Enquiry saved with reference {result.get('id')}. "
                "It is pending staff confirmation; no ride is booked yet."
            )
        except Exception:
            log.exception("Could not save booking enquiry")
            return (
                "I could not save that enquiry. Offer a staff callback "
                "and do not claim it was booked."
            )

    @function_tool
    async def capture_customer_lead(
        self,
        customer_name: str,
        phone: str,
        interest: str,
        city: str,
        notes: str = "",
    ) -> str:
        """Save a potential customer, driver, fleet-owner or investor lead."""
        try:
            result = await submit_intake("lead", {
                "customer_name": customer_name,
                "phone": phone,
                "interest": interest,
                "city": city,
                "notes": notes,
            })
            return f"Lead saved with reference {result.get('id')}."
        except Exception:
            log.exception("Could not save customer lead")
            return "I could not save the lead. Offer a staff callback instead."

server = AgentServer()

@server.rtc_session(agent_name="met-ride-receptionist")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=openai.STT(model="gpt-4o-mini-transcribe"),
        llm=openai.responses.LLM(model="gpt-4.1"),
        tts=openai.TTS(model="gpt-4o-mini-tts", voice="alloy"),
        vad=silero.VAD.load(),
    )
    await session.start(room=ctx.room, agent=MetRideReceptionist())
    await session.generate_reply(
        instructions=(
            "Greet the caller as Alex from MET RIDE. "
            "Ask whether they prefer English or Hausa."
        )
    )

if __name__ == "__main__":
    cli.run_app(server)
