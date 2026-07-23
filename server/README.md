# Running the test environment:

- cd server
- uv sync
- uv run test.py console

Note: Make sure you have .env and creds.json in the server directory.

## Outbound phone calls (Plivo SIP)

Set `SIP_OUTBOUND_TRUNK_ID` in `server/.env` to your LiveKit outbound trunk ID
(from `lk sip outbound list`). The frontend `/api/outbound-call` route dispatches
`demo-agent` with `phone_number` in job metadata; the agent dials via
`CreateSIPParticipant`.
