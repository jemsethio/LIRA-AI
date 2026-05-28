"use client";
import { useLocale, useTranslations } from "next-intl";
import { useRouter, usePathname } from "@/i18n/navigation";

const LOCALES = [
  { code: "en", label: "EN" },
  { code: "am", label: "አማ" },
  { code: "om", label: "OM" },
] as const;

export default function LocaleSwitcher() {
  const locale = useLocale();
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname(); // returns path WITHOUT locale prefix

  return (
    <div
      role="group"
      aria-label={t("locale.switcherLabel")}
      className="flex items-center"
    >
      {LOCALES.map(({ code, label }, i) => (
        <span key={code} className="flex items-center">
          {i > 0 && (
            <span className="w-px h-4 bg-lira-border mx-1" aria-hidden="true" />
          )}
          <button
            onClick={() => router.replace(pathname, { locale: code })}
            aria-pressed={locale === code}
            aria-label={t(`locale.label.${code}`)}
            className={[
              "px-2 min-h-touch min-w-[32px] text-xs transition-colors",
              locale === code
                ? "text-lira-green-aa font-semibold"
                : "text-lira-muted-aa hover:text-slate-200",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[#9db8cc] focus-visible:ring-offset-2",
              "focus-visible:ring-offset-lira-bg rounded",
            ].join(" ")}
          >
            {label}
          </button>
        </span>
      ))}
    </div>
  );
}
