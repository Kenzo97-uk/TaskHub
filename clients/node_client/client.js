import axios from "axios";
import WebSocket from "ws";

const API_URL = process.env.API_URL || "http://localhost:8000/";
const WS_URL = process.env.WS_URL || "ws://localhost:8000/ws";
const API_KEY = process.env.API_KEY || "changeme-super-secret";

const headers = { "X-API-Key": API_KEY };

function startWs() {
  console.log("== WebSocket demo (Node client) ==");
  const ws = new WebSocket(WS_URL);

  ws.on("open", () => {
    console.log("WS connected");
    setInterval(() => ws.send("ping"), 5000);
  });

  ws.on("message", (data) => {
    console.log("WS event:", data.toString());
  });

  ws.on("close", () => console.log("WS closed"));
  ws.on("error", (err) => console.error("WS error:", err));
}

async function restDemo() {
  console.log("== REST demo (Node client) ==");

  const created = (await axios.post(`${API_URL}tasks`, { title: "Read PAR docs", done: false }, { headers })).data;
  console.log("Created:", created);

  const updated = (await axios.put(`${API_URL}tasks/${created.id}`, { title: "Read PAR docs (done)", done: true }, { headers })).data;
  console.log("Updated:", updated);

  const list = (await axios.get(`${API_URL}tasks`, { headers })).data;
  console.log("All tasks:", list);
}

startWs();
setTimeout(() => {
  restDemo().catch((e) => console.error(e?.response?.data || e.message));
}, 1000);

setTimeout(() => process.exit(0), 12000);
