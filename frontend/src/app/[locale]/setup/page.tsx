"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { createProject } from "@/lib/api";

const LANDSCAPE_TYPES = ["watershed", "woreda", "kebele", "rangeland", "reservoir_catchment", "custom"];
const OBJECTIVES = [
  "erosion_control", "water_security", "food_security",
  "biodiversity", "carbon_sequestration", "rangeland_restoration", "integrated",
];

export default function SetupPage() {
  const t = useTranslations("setup");
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    country: "Ethiopia",
    region: "",
    admin_level: "",
    landscape_type: "watershed",
    target_objective: "integrated",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const project = await createProject(form) as { id: string };
      router.push(`/diagnosis?project=${project.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-1">{t("title")}</h1>
      <p className="text-lira-muted text-sm mb-8">Define the landscape boundary and project scope</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div>
          <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">
            Project Name *
          </label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Amhara Highland Kebele — Watershed 2025"
            className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60"
          />
        </div>

        {/* Country / Region */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Country</label>
            <input
              type="text"
              value={form.country}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
              className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-lira-green/60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Region *</label>
            <input
              type="text"
              required
              value={form.region}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
              placeholder="e.g. Amhara, Tigray, Oromia"
              className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60"
            />
          </div>
        </div>

        {/* Admin level */}
        <div>
          <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Admin Level</label>
          <input
            type="text"
            value={form.admin_level}
            onChange={(e) => setForm({ ...form, admin_level: e.target.value })}
            placeholder="e.g. Kebele, Woreda, Zone"
            className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60"
          />
        </div>

        {/* Landscape type */}
        <div>
          <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Landscape Type</label>
          <select
            value={form.landscape_type}
            onChange={(e) => setForm({ ...form, landscape_type: e.target.value })}
            className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-lira-green/60"
          >
            {LANDSCAPE_TYPES.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>

        {/* Target objective */}
        <div>
          <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Target Objective</label>
          <select
            value={form.target_objective}
            onChange={(e) => setForm({ ...form, target_objective: e.target.value })}
            className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-lira-green/60"
          >
            {OBJECTIVES.map((o) => (
              <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-lira-muted mb-1.5 uppercase tracking-wide">Notes</label>
          <textarea
            rows={3}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Context, objectives, known constraints..."
            className="w-full bg-lira-surface border border-lira-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60 resize-none"
          />
        </div>

        {error && (
          <div className="text-red-400 text-sm bg-red-900/20 border border-red-900/40 rounded-lg px-4 py-2">
            {t("error")}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-lira-green text-white py-3 rounded-lg font-medium text-sm hover:bg-lira-green/80 transition disabled:opacity-50"
        >
          {loading ? t("loading") : t("submitButton")}
        </button>
      </form>
    </div>
  );
}
