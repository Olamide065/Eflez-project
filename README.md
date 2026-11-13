# MET RIDE AI

Cloud-hosted AI voice receptionist for MET RIDE / Mettle Paragon International Limited.

## Included
- LiveKit Agents voice receptionist
- OpenAI speech-to-text, language model and text-to-speech
- Booking enquiry and customer lead tools
- Supabase intake endpoint integration

## Local setup
1. Install Python 3.11–3.13 and uv.
2. Copy `.env.example` to `.env`.
3. Add your own OpenAI key and the Supabase intake secret to `.env`.
4. Run `uv sync`.
5. Run `uv run python src/agent.py download-files`.
6. Run `uv run python src/agent.py console`.

Never commit `.env`, API keys, service-role keys, or shared secrets.

## Deployment
Deploy the agent to LiveKit Cloud and configure OPENAI_API_KEY,
SUPABASE_URL, and MET_RIDE_INGEST_SECRET as deployment secrets.
LiveKit supplies its own connection credentials at runtime.

Phone calls require a compatible SIP trunk provider. Human transfer,
WhatsApp, payment verification, outbound calling and recording controls
require additional integrations and testing before production use.
