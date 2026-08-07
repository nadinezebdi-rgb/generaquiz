import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from "recharts";
import { Brain, Info, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

/**
 * MemoryScoreRadar — 5 cognitive axes visualisation (Sprint C).
 *
 * Data source: GET /api/progression/memory-score
 * Each axis is a 0-100 score computed server-side from existing attempts /
 * daily_attempts / user_category_stats — never trust the client.
 */

const OVERALL_TIER = [
  { min: 85, label: "Exceptionnel",   color: "text-bordeaux",       bg: "bg-bordeaux/10" },
  { min: 70, label: "Très bon",       color: "text-terracotta",     bg: "bg-terracotta/10" },
  { min: 50, label: "Bon rythme",     color: "text-[#2A7350]",      bg: "bg-[#3D9970]/10" },
  { min: 30, label: "En progrès",     color: "text-mustard-dark",   bg: "bg-mustard/20" },
  { min: 0,  label: "Cold start",     color: "text-navy/60",        bg: "bg-cream-dark" },
];

function tierFor(overall) {
  return OVERALL_TIER.find((t) => overall >= t.min) || OVERALL_TIER[OVERALL_TIER.length - 1];
}

export default function MemoryScoreRadar() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api
      .get("/progression/memory-score")
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white border-2 border-cream-dark rounded-[28px] p-5 md:p-7 mb-6 flex items-center justify-center min-h-[280px]" data-testid="memory-score-loading">
        <Loader2 className="w-6 h-6 animate-spin text-terracotta" />
      </div>
    );
  }
  if (!data) return null;

  const tier = tierFor(data.overall);
  const chartData = data.axes.map((a) => ({
    axis: a.label,
    key: a.key,
    value: a.value,
    hint: a.hint,
    detail: a.detail,
  }));
  const focus = selected || chartData[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-white border-2 border-cream-dark rounded-[28px] p-5 md:p-7 mb-6"
      data-testid="memory-score-card"
    >
      <div className="flex items-start gap-3 mb-4 flex-wrap">
        <div className="w-11 h-11 rounded-2xl bg-terracotta/15 flex items-center justify-center shrink-0">
          <Brain className="w-5 h-5 text-terracotta" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="font-display text-2xl font-bold text-navy">Score Mémoire</h2>
          <p className="text-sm text-navy/60">
            Cinq axes cognitifs mis à jour à chaque quiz. Cliquez sur un point pour comprendre.
          </p>
        </div>
        <div className={`text-right px-4 py-2 rounded-2xl ${tier.bg}`} data-testid="memory-score-overall">
          <div className={`text-xs font-bold uppercase tracking-wider ${tier.color}`}>{tier.label}</div>
          <div className="font-display text-3xl font-extrabold text-navy leading-none">
            {data.overall}
            <span className="text-base text-navy/60 font-bold">/100</span>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-5 gap-4 items-center">
        <div className="md:col-span-3">
          <div className="w-full h-[280px] md:h-[320px]" data-testid="memory-score-radar">
            <ResponsiveContainer>
              <RadarChart data={chartData} outerRadius="72%">
                <PolarGrid stroke="#E8DFC7" />
                <PolarAngleAxis
                  dataKey="axis"
                  tick={{ fill: "#1F2A44", fontSize: 12, fontWeight: 700 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fill: "#1F2A44", opacity: 0.4, fontSize: 10 }}
                  tickCount={5}
                />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke="#C25E3D"
                  strokeWidth={2}
                  fill="#C25E3D"
                  fillOpacity={0.35}
                  activeDot={{
                    r: 6,
                    onClick: (_, ev) => {
                      const idx = ev?.payload?.index;
                      if (typeof idx === "number") setSelected(chartData[idx]);
                    },
                  }}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "2px solid #E8DFC7",
                    fontFamily: "inherit",
                  }}
                  formatter={(v) => [`${v}/100`, "Score"]}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="md:col-span-2 space-y-2">
          {chartData.map((a) => {
            const isFocus = focus?.key === a.key;
            return (
              <button
                key={a.key}
                type="button"
                onClick={() => setSelected(a)}
                data-testid={`memory-axis-${a.key}`}
                className={`w-full text-left rounded-2xl p-3 border-2 transition ${
                  isFocus
                    ? "bg-cream border-terracotta"
                    : "bg-white border-cream-dark hover:border-terracotta/40"
                }`}
              >
                <div className="flex items-center justify-between mb-1 gap-2">
                  <span className="font-bold text-navy text-sm">{a.axis}</span>
                  <span
                    className="font-display text-lg font-extrabold text-terracotta"
                    data-testid={`memory-axis-${a.key}-value`}
                  >
                    {a.value}
                  </span>
                </div>
                <div className="h-1.5 bg-cream-dark rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-terracotta"
                    initial={{ width: 0 }}
                    animate={{ width: `${a.value}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {focus && (
        <motion.div
          key={focus.key}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 bg-cream border-2 border-cream-dark rounded-2xl p-3 flex items-start gap-2"
          data-testid="memory-axis-focus"
        >
          <Info className="w-4 h-4 text-terracotta shrink-0 mt-0.5" />
          <div className="text-sm text-navy/80">
            <strong className="text-navy">{focus.axis} — {focus.value}/100.</strong> {focus.hint}.
            {focus.detail?.cold_start && (
              <span className="text-terracotta font-medium"> Encore trop peu de données — jouez quelques quiz pour affiner ce score.</span>
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
