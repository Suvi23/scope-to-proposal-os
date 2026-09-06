from src.extractor import extract_requirements


client_request = """
We run a dental clinic with 3 branches. Most enquiries come
through WhatsApp and Instagram and staff keeps answering the
same questions.

We want an AI chatbot that can answer everything, qualify
patients, book appointments, follow up with people who don't
respond, update our CRM, send reminders and maybe handle
phone calls too.

It should work in English, Hindi and Marathi, never make
mistakes, and we want it live in 3 days.

We already have a CRM but I'm not sure if it has an API.

We mainly want more bookings.
"""


result = extract_requirements(client_request)

print("\n========== REQUIREMENT MAP ==========\n")

print(result.model_dump_json(indent=2))