import agentRoutes from "./routes/agent.routes.js";
import express from "express";
import cors from "cors";

const app = express();

app.use(cors());
app.use(express.json());

app.get("/health", (req, res) => {
  res.json({ status: "Agent backend running" });
});

app.use("/agent", agentRoutes);

export default app;