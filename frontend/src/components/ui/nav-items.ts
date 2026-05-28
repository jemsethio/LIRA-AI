import {
  LayoutDashboard, FlaskConical, CloudLightning,
  GitBranch, Sprout, Scale, Landmark, Users, FileDown,
  Folders, Database, Activity, MessageSquare, Globe, Map,
  BookOpen, Cpu,
} from "lucide-react";

export const NAV = [
  { href: "/",            labelKey: "nav.items.projects",   icon: Folders,        group: "core" },
  { href: "/setup",       labelKey: "nav.items.setup",      icon: LayoutDashboard, group: "core" },
  { href: "/omo-ghibe",   labelKey: "nav.items.omoGhibe",   icon: Globe,          group: "core" },
  { href: "/climate-data",labelKey: "nav.items.climateData",icon: CloudLightning, group: "core" },
  { href: "/map",          labelKey: "nav.items.map",        icon: Map,             group: "analysis" },
  { href: "/evidence",    labelKey: "nav.items.evidence",   icon: Database,        group: "analysis" },
  { href: "/diagnosis",   labelKey: "nav.items.diagnosis",  icon: FlaskConical,    group: "analysis" },
  { href: "/climate",     labelKey: "nav.items.climate",    icon: CloudLightning,  group: "analysis" },
  { href: "/syndromes",   labelKey: "nav.items.syndromes",  icon: GitBranch,      group: "analysis" },
  { href: "/pathways",    labelKey: "nav.items.pathways",   icon: Sprout,          group: "planning" },
  { href: "/tradeoffs",   labelKey: "nav.items.tradeoffs",  icon: Scale,           group: "planning" },
  { href: "/investment",  labelKey: "nav.items.investment", icon: Landmark,        group: "planning" },
  { href: "/community",   labelKey: "nav.items.community",  icon: Users,           group: "planning" },
  { href: "/advisory",    labelKey: "nav.items.advisory",   icon: MessageSquare,   group: "planning" },
  { href: "/monitoring",  labelKey: "nav.items.monitoring", icon: Activity,        group: "learning" },
  { href: "/knowledge",   labelKey: "nav.items.knowledge",  icon: BookOpen,        group: "learning" },
  { href: "/mcp-tools",   labelKey: "nav.items.mcpTools",   icon: Cpu,             group: "learning" },
  { href: "/export",      labelKey: "nav.items.export",     icon: FileDown,        group: "learning" },
];

export const GROUP_LABELS: Record<string, string> = {
  core:     "Pilot",
  analysis: "Analysis",
  planning: "Planning",
  learning: "Knowledge & Export",
};
