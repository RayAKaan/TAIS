TAIS-LANG v3: Living Speech
No LLM, no pretrained language model, no codebook sentence generation.

This version gives motes a primitive speech organ:

  Mote state -> intent -> private lexicon -> token utterance -> listener interpretation -> action -> survival feedback -> lexicon update

Files
  swarm_v3.py     - Living Speech Flask/SSE backend.
  src/App.jsx     - React/Vite interface for v3 speech, teaching, silence, and lexicon inspection.

Run v3
  Terminal 1:
    python3 -m pip install -r requirements.txt
    python3 swarm_v3.py

  Terminal 2:
    npm install
    npm run dev

  Open: http://localhost:5173
  Backend: http://localhost:5123

What you can do
  - Move yourself on the grid.
  - Send raw sounds/words into the swarm.
  - Teach a word by grounding it in a concept, e.g. food -> FOOD_HIGH.
  - Watch motes emit their own tokens, not generated English.
  - Hover motes to inspect their private lexicon and grammar genome.
  - Watch silence appear as a logged decision.
  - Watch predators follow advertised signal content.

Useful endpoints
  GET  /stream            - SSE live state
  GET  /state             - JSON snapshot
  GET  /health            - health check
  POST /player/move       - { "x": 2, "y": 2 }
  POST /player/speak      - { "text": "food", "fitness": 10, "x": 2, "y": 2 }
  POST /player/teach      - { "word": "food", "concept": "FOOD_HIGH" }
  GET  /mote/<id>/lexicon - inspect private lexicon
  POST /reset             - reset swarm
