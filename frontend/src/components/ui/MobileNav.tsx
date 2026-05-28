"use client";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "@/i18n/navigation";
import { Menu, X } from "lucide-react";
import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { NAV } from "./nav-items";
import LocaleSwitcher from "./LocaleSwitcher";

export default function MobileNav() {
  const path = usePathname();
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const groups = ["core", "analysis", "planning", "learning"];

  const hamburgerRef = useRef<HTMLButtonElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);

  // Close drawer on Escape keydown (T-09-01-01 mitigation)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus management: move focus to first link on open, back to hamburger on close
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => firstLinkRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    } else {
      hamburgerRef.current?.focus();
    }
  }, [open]);

  return (
    <div className="lg:hidden">
      {/* Top bar */}
      <div className="h-14 px-4 flex items-center justify-between bg-lira-surface border-b border-lira-border sticky top-0 z-40">
        {/* Hamburger */}
        <button
          ref={hamburgerRef}
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? t('nav.close') : t('nav.open')}
          aria-expanded={open}
          className="min-h-touch min-w-touch flex items-center justify-center text-slate-200 hover:text-lira-green transition-colors"
        >
          {open ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
        </button>

        {/* Brand */}
        <span className="text-sm font-bold text-lira-green">LIRA-AI</span>

        {/* Connection status pill */}
        <div className="flex items-center gap-1.5 text-xs text-lira-green">
          <span className="w-2 h-2 rounded-full bg-lira-green animate-pulse" aria-hidden="true" />
          <span className="text-xs text-lira-muted-aa">Online</span>
        </div>

        {/* Locale switcher */}
        <div className="shrink-0"><LocaleSwitcher /></div>
      </div>

      {/* Scrim */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      {/* NOTE: role="dialog" overrides the nav landmark. Phase 10 defers restructuring
          per research open question — this is flagged for axe-core review. */}
      <nav
        role="dialog"
        aria-modal="true"
        aria-label={t('nav.primary')}
        className="fixed inset-y-0 left-0 z-50 w-72 bg-lira-surface flex flex-col shadow-2xl transform transition-transform duration-200 ease-out lg:hidden"
        style={{ transform: open ? "translateX(0)" : "translateX(-100%)" }}
      >
        {/* Brand header */}
        <div className="px-4 py-4 border-b border-lira-border shrink-0">
          <div className="text-lira-green font-bold text-base tracking-wide leading-snug">
            LIRA-AI
          </div>
          <div className="text-xs text-lira-muted-aa leading-snug mt-0.5">
            Landscape Intelligence for Regeneration and Adaptation
          </div>
          <div className="mt-3 pt-2 border-t border-lira-border/50">
            <Image
              src="/logos/Alliance+CGIAR-WHITE.png"
              alt="Alliance of Bioversity International and CIAT | CGIAR"
              width={876}
              height={346}
              className="w-full h-auto object-contain opacity-80"
            />
          </div>
        </div>

        {/* Nav links */}
        <ul className="flex-1 overflow-y-auto py-2 px-2">
          {groups.map((group) => {
            const items = NAV.filter((n) => n.group === group);
            return (
              <li key={group} className="mb-1">
                <div
                  id={`mobile-nav-group-${group}`}
                  className="text-xs font-semibold text-lira-muted-aa uppercase tracking-widest px-4 py-2"
                >
                  {t(`nav.group.${group}`)}
                </div>
                <ul aria-labelledby={`mobile-nav-group-${group}`}>
                  {items.map(({ href, labelKey, icon: Icon }) => {
                    const active = path === href || (href !== "/" && path.startsWith(href));
                    return (
                      <li key={href}>
                        <Link
                          href={href}
                          ref={href === "/" ? firstLinkRef : undefined}
                          onClick={() => setOpen(false)}
                          aria-current={active ? "page" : undefined}
                          className={clsx(
                            "min-h-[44px] flex items-center gap-3 px-4 py-3 rounded-md text-sm transition-colors mb-0.5",
                            active
                              ? "bg-lira-green/20 text-lira-green-aa font-medium"
                              : "text-lira-muted-aa hover:bg-lira-border/40 hover:text-slate-200"
                          )}
                        >
                          <Icon size={16} strokeWidth={1.8} aria-hidden="true" />
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

        {/* Footer */}
        <div className="px-4 py-3 border-t border-lira-border text-xs text-lira-muted-aa shrink-0">
          <div className="flex items-center gap-1.5">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="2"/>
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
            </svg>
            <a href="mailto:J.Ahmed@cgiar.org" aria-label={t('nav.contactEmail')} className="hover:text-lira-green transition-colors">
              J.Ahmed@cgiar.org
            </a>
          </div>
          <div className="opacity-50 mt-0.5">MVP v0.1 · Ethiopia</div>
        </div>
      </nav>
    </div>
  );
}
