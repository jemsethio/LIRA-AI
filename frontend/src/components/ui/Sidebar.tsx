"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "@/i18n/navigation";
import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { NAV } from "./nav-items";
import LocaleSwitcher from "./LocaleSwitcher";

export default function Sidebar() {
  const path = usePathname();
  const t = useTranslations();
  const groups = ["core", "analysis", "planning", "learning"];

  return (
    <nav aria-label={t('nav.primary')} className="w-64 shrink-0 flex flex-col bg-lira-surface border-r border-lira-border h-screen">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-lira-border">
        <div className="mb-1">
          <div className="text-lira-green font-bold text-base tracking-wide leading-snug">
            LIRA-AI
          </div>
          <div className="text-xs text-lira-muted-aa leading-snug mt-0.5">
            Landscape Intelligence for Regeneration
          </div>
          <div className="text-xs text-lira-muted-aa leading-snug">
            and Adaptation
          </div>
        </div>

        {/* Partner logo */}
        <div className="mt-3 pt-2 border-t border-lira-border/50">
          <Image
            src="/logos/Alliance+CGIAR-WHITE.png"
            alt="Alliance of Bioversity International and CIAT | CGIAR"
            width={876}
            height={346}
            className="w-full h-auto object-contain opacity-80 hover:opacity-100 transition-opacity"
          />
        </div>
      </div>

      {/* Nav */}
      <ul className="flex-1 overflow-y-auto py-2 px-2">
        {groups.map((group) => {
          const items = NAV.filter((n) => n.group === group);
          return (
            <li key={group} className="mb-1">
              <div
                id={`nav-group-${group}`}
                className="px-3 py-1.5 text-xs font-semibold text-lira-muted-aa uppercase tracking-widest"
              >
                {t(`nav.group.${group}`)}
              </div>
              <ul aria-labelledby={`nav-group-${group}`}>
                {items.map(({ href, labelKey, icon: Icon }) => {
                  const active = path === href || (href !== "/" && path.startsWith(href));
                  return (
                    <li key={href}>
                      <Link
                        href={href}
                        aria-current={active ? "page" : undefined}
                        className={clsx(
                          "flex items-center gap-2.5 px-3 py-1.5 rounded-md text-xs transition-colors mb-0.5",
                          active
                            ? "bg-lira-green/20 text-lira-green-aa font-medium"
                            : "text-lira-muted-aa hover:bg-lira-border/40 hover:text-slate-200"
                        )}
                      >
                        <Icon size={13} strokeWidth={1.8} aria-hidden="true" />
                        {t(labelKey)}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </li>
          );
        })}
      </ul>

      {/* Bottom contact */}
      <div className="px-4 py-3 border-t border-lira-border text-xs text-lira-muted-aa space-y-0.5">
        <div className="flex items-center gap-1.5">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="2" y="4" width="20" height="16" rx="2"/>
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
          </svg>
          <a href="mailto:J.Ahmed@cgiar.org" aria-label={t('nav.contactEmail')} className="hover:text-lira-green transition-colors">
            J.Ahmed@cgiar.org
          </a>
        </div>
        <LocaleSwitcher />
      </div>
    </nav>
  );
}
