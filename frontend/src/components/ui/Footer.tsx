import Image from "next/image";
import { getTranslations } from "next-intl/server";

export default async function Footer() {
  const t = await getTranslations();

  return (
    <footer aria-label={t('nav.siteFooter')} className="border-t border-lira-border bg-lira-surface mt-auto shrink-0">
      <div className="max-w-7xl mx-auto px-6 py-4">
        {/* Logo + info row */}
        <div className="flex items-center justify-between gap-6 flex-wrap">

          {/* Alliance + CGIAR logo */}
          <a
            href="https://alliancebioversityciat.org"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity shrink-0"
          >
            <Image
              src="/logos/Alliance+CGIAR-WHITE.png"
              alt="Alliance of Bioversity International and CIAT | CGIAR"
              width={876}
              height={346}
              className="h-10 w-auto object-contain"
              priority
            />
          </a>

          {/* Centre: project identity */}
          <div className="text-center flex-1 min-w-0">
            <div className="text-[11px] font-semibold text-slate-300">
              LIRA-AI: Landscape Intelligence for Regeneration and Adaptation
            </div>
            <div className="text-[10px] text-lira-muted mt-0.5">
              Alliance Bioversity International - CIAT Addis Ababa, Ethiopia · Ethiopia Living Lab · Omo-Ghibe Basin · MVP v0.1
            </div>
          </div>

          {/* Contact */}
          <div className="text-[11px] text-lira-muted text-right shrink-0">
            <a
              href="mailto:J.Ahmed@cgiar.org"
              className="flex items-center gap-1.5 hover:text-lira-green transition-colors justify-end"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" className="opacity-70 shrink-0">
                <rect x="2" y="4" width="20" height="16" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              J.Ahmed@cgiar.org
            </a>
            <div className="text-[10px] opacity-50 mt-0.5">
              © {new Date().getFullYear()} CGIAR · All data sources cited
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
