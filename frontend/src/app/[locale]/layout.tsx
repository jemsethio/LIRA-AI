import { Noto_Serif_Ethiopic } from "next/font/google";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import { NextIntlClientProvider } from "next-intl";
import { routing } from "@/i18n/routing";
import Sidebar from "@/components/ui/Sidebar";
import MobileNav from "@/components/ui/MobileNav";
import Footer from "@/components/ui/Footer";
import SWRegister from "@/components/offline/SWRegister";
import OfflineBanner from "@/components/ui/OfflineBanner";

const notoEthiopic = Noto_Serif_Ethiopic({
  subsets: ["ethiopic"],
  weight: ["400", "600"],
  variable: "--font-ethiopic",
  display: "swap",
  preload: false,
});

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  const messages = await getMessages();
  const tA11y = await getTranslations("a11y");

  return (
    <html lang={locale} className={notoEthiopic.variable}>
      <body suppressHydrationWarning className="flex flex-col lg:flex-row h-screen bg-lira-bg text-slate-200 overflow-hidden">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <a href="#main-content" className="skip-link">
            {tA11y("skipToMain")}
          </a>
          <div className="hidden lg:block">
            <Sidebar />
          </div>
          <MobileNav />
          <div className="flex flex-col flex-1 overflow-hidden min-w-0">
            <OfflineBanner />
            <main id="main-content" className="flex-1 overflow-y-auto">
              {children}
            </main>
            <Footer />
          </div>
          <SWRegister />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
