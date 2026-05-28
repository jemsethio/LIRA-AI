import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LIRA-AI: Landscape Intelligence for Regeneration and Adaptation",
  description:
    "Predictive intelligence for investable landscape regeneration — CGIAR MFL, CASP Living Lab, Omo-Ghibe Basin, Ethiopia",
  keywords: ["LIRA-AI", "landscape restoration", "CGIAR", "MFL", "Ethiopia", "Omo-Ghibe", "climate adaptation"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children as React.ReactElement;
}
