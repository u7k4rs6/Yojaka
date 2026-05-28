"""
Smoke test: complete a Mock-provider debate end-to-end via WebSocket.
Run with: python tests/smoke_ws.py
"""
import asyncio
import json
import sys
import httpx
import websockets

API = "http://localhost:8000"
WS  = "ws://localhost:8000"


async def main():
    client_id = "smoke-ws-test"

    async with httpx.AsyncClient() as http:
        # Create session
        r = await http.post(
            f"{API}/api/sessions",
            json={"name": "Smoke WS", "mode": "ai_vs_ai", "settings": {}},
            headers={"X-Client-ID": client_id},
        )
        assert r.status_code == 201, f"create session failed: {r.status_code} {r.text}"
        session = r.json()
        sid = session["id"]
        print(f"[smoke] Created session {sid}")

    # Connect WebSocket
    uri = f"{WS}/ws/debates/{sid}?client_id={client_id}"
    events = []

    async with websockets.connect(uri) as ws:
        print("[smoke] WS connected, starting debate …")
        await ws.send(json.dumps({
            "type":  "start_debate",
            "topic": "AI will surpass human intelligence within 20 years",
            "model": "mock-debate-model",
        }))

        deadline = asyncio.get_event_loop().time() + 30  # 30s timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                print("[smoke] TIMEOUT waiting for debate_completed", file=sys.stderr)
                sys.exit(1)
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                print("[smoke] TIMEOUT", file=sys.stderr)
                sys.exit(1)

            ev = json.loads(raw)
            events.append(ev["type"])
            print(f"[smoke] ← {ev['type']}")

            if ev["type"] in ("debate_completed", "early_stop", "error"):
                if ev["type"] == "error":
                    print(f"[smoke] ERROR: {ev.get('message')}", file=sys.stderr)
                    sys.exit(1)
                break

    required = {"debate_started", "message_started", "message_completed"}
    missing  = required - set(events)
    if missing:
        print(f"[smoke] MISSING events: {missing}", file=sys.stderr)
        sys.exit(1)

    print(f"[smoke] PASS — {len(events)} events received")


if __name__ == "__main__":
    asyncio.run(main())
