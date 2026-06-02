"use client";

import {
  BarChart3,
  CheckSquare,
  FileText,
  LayoutDashboard,
  Menu,
  MessageSquareText,
  Plug,
  Search,
  Settings,
  Video,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { LogoutButton } from "@/components/logout-button";
import type { SearchItem } from "@/lib/dashboard-ui";
import { supabaseBrowserClient } from "@/lib/supabase/client";

const mainNav = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, badge: null },
  { label: "Meetings", href: "/meetings", icon: Video, badge: "1" },
  { label: "Tasks", href: "/tasks", icon: CheckSquare, badge: "0" },
  { label: "Transcripts", href: "/transcripts", icon: FileText, badge: null },
  { label: "AI Chat", href: "/ai-chat", icon: MessageSquareText, badge: null },
];

const workspaceNav = [
  { label: "Insights", href: "/analytics", icon: BarChart3, badge: null },
  { label: "Integrations", href: "/integrations", icon: Plug, badge: null },
];

const accountNav = [{ label: "Settings", href: "/settings/meeting-assistant", icon: Settings, badge: null }];

const baseSearchItems: SearchItem[] = [...mainNav, ...workspaceNav, ...accountNav].map((item) => ({
  id: `nav-${item.href}`,
  label: item.label,
  description: "Open workspace section",
  href: item.href,
  category: "Navigation",
}));

type CalendarUser = {
  name: string;
  email: string;
  initials: string;
};

export function AppShell({
  children,
  searchItems = [],
}: {
  children: ReactNode;
  searchItems?: SearchItem[];
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [calendarUser, setCalendarUser] = useState<CalendarUser>({
    name: "Calendar user",
    email: "Not connected",
    initials: "CU",
  });

  useEffect(() => {
    let mounted = true;

    async function loadUser() {
      const {
        data: { session },
      } = await supabaseBrowserClient.auth.getSession();
      if (!mounted) {
        return;
      }

      const user = session?.user;
      const metadata = user?.user_metadata ?? {};
      const name =
        asString(metadata.full_name) ??
        asString(metadata.name) ??
        asString(metadata.preferred_username) ??
        user?.email ??
        "Calendar user";
      const email = user?.email ?? asString(metadata.email) ?? "Calendar not connected";
      setCalendarUser({
        name,
        email,
        initials: initialsFor(name, email),
      });
    }

    void loadUser();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    setIsPanelOpen(false);
    setIsProfileOpen(false);
    setQuery("");
  }, [pathname]);

  const filteredSearchItems = useMemo(() => {
    const items = [...baseSearchItems, ...searchItems];
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return items.slice(0, 6);
    }
    return items
      .filter((item) =>
        [item.label, item.description, item.category].some((value) =>
          value.toLowerCase().includes(normalized),
        ),
      )
      .slice(0, 8);
  }, [query, searchItems]);

  function openSearchResult(item: SearchItem) {
    setQuery("");
    router.push(item.href);
  }

  return (
    <main className="min-h-screen bg-shell">
      <header className="grid min-h-20 grid-cols-[220px_minmax(260px,1fr)_auto] items-center gap-4 border-b border-line bg-white px-6">
        <div className="flex items-center gap-2">
          <img
            src="/aress_software_logo.png"
            alt="Aress logo"
            className="size-12 shrink-0 rounded-[8px] object-contain"
          />
          <span className="truncate text-sm font-semibold tracking-[-0.2px] text-ink">aress MeetIQ</span>
        </div>

        <div className="relative mx-auto w-full max-w-[460px]">
          <div className="flex h-9 items-center gap-2 rounded-[10px] border border-line bg-[#efefeb] px-3 text-xs text-ink focus-within:border-brand focus-within:bg-white focus-within:shadow-[0_0_0_3px_rgba(61,53,176,0.12)]">
            <Search size={14} className="shrink-0 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && filteredSearchItems[0]) {
                  openSearchResult(filteredSearchItems[0]);
                }
                if (event.key === "Escape") {
                  setQuery("");
                }
              }}
              placeholder="Search meetings, tasks..."
              className="h-full min-w-0 flex-1 bg-transparent text-xs text-ink outline-none placeholder:text-[#a8a8a3]"
              aria-label="Search meetings, tasks, and sections"
            />
          </div>
          {query.trim() ? (
            <div className="absolute left-0 right-0 top-11 z-30 max-h-[320px] overflow-auto rounded-[12px] border border-line bg-white p-2 shadow-[0_16px_40px_rgba(26,26,24,0.12)]">
              {filteredSearchItems.length ? (
                filteredSearchItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => openSearchResult(item)}
                    className="flex w-full items-center justify-between gap-3 rounded-[9px] px-3 py-2 text-left hover:bg-[#faf9f5]"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-medium text-ink">{item.label}</span>
                      <span className="mt-0.5 block truncate text-[11px] text-muted">
                        {item.category} - {item.description}
                      </span>
                    </span>
                    <span className="shrink-0 text-[10px] font-medium text-brand-dark">Open</span>
                  </button>
                ))
              ) : (
                <p className="px-3 py-4 text-center text-xs text-muted">No results found.</p>
              )}
            </div>
          ) : null}
        </div>

        <div className="flex items-center gap-2 justify-self-end">
          <div className="relative">
            <button
              id="profile-menu-button"
              type="button"
              onClick={() => setIsProfileOpen((current) => !current)}
              className="grid size-9 place-items-center rounded-full border border-line bg-white p-0 hover:bg-[#faf9f5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-white"
              aria-label={`${isProfileOpen ? "Close" : "Open"} profile menu for ${calendarUser.name}`}
              aria-expanded={isProfileOpen}
              aria-controls="profile-menu"
            >
              <span className="grid size-[30px] shrink-0 place-items-center rounded-full bg-brand-soft text-[11px] font-semibold text-brand-dark">
                {calendarUser.initials}
              </span>
            </button>
            {isProfileOpen ? (
              <div
                id="profile-menu"
                aria-labelledby="profile-menu-button"
                className="absolute right-0 top-11 z-30 w-[260px] rounded-[14px] border border-line bg-white p-3 shadow-[0_16px_40px_rgba(26,26,24,0.12)]"
              >
                <div className="border-b border-line pb-3">
                  <p className="truncate text-sm font-semibold text-ink">{calendarUser.name}</p>
                  <p className="mt-1 truncate text-xs text-muted">{calendarUser.email}</p>
                </div>
                <LogoutButton variant="menu" className="mt-3" />
              </div>
            ) : null}
          </div>

          <button
            type="button"
            onClick={() => setIsPanelOpen(true)}
            className="inline-grid size-9 place-items-center rounded-[10px] border border-line bg-[#efefeb] text-ink transition hover:border-brand hover:bg-white hover:text-brand-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            aria-label="Open navigation menu"
            aria-expanded={isPanelOpen}
            aria-controls="app-navigation-panel"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
        </div>
      </header>

      {isPanelOpen ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 bg-ink/25"
            onClick={() => setIsPanelOpen(false)}
            aria-label="Close navigation overlay"
          />
          <aside
            id="app-navigation-panel"
            className="absolute right-0 top-0 flex h-full w-[280px] flex-col border-l border-line bg-white px-3 py-4 shadow-[-24px_0_48px_rgba(26,26,24,0.18)]"
          >
            <div className="mb-6 flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <img
                  src="/aress_software_logo.png"
                  alt="Aress logo"
                  className="size-12 shrink-0 rounded-[8px] object-contain"
                />
                <span className="text-sm font-semibold text-ink">aress MeetIQ</span>
              </div>
              <button
                type="button"
                onClick={() => setIsPanelOpen(false)}
                className="grid size-8 place-items-center rounded-[9px] border border-line bg-[#efefeb] text-muted"
                aria-label="Close navigation"
              >
                <X size={15} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              <NavGroup title="Main" items={mainNav} pathname={pathname} />
              <NavGroup title="Workspace" items={workspaceNav} pathname={pathname} />
            </div>
            <div className="border-t border-line pt-4">
              <NavGroup title="Account" items={accountNav} pathname={pathname} />
            </div>
          </aside>
        </div>
      ) : null}

      <section className="min-h-[calc(100vh-80px)] min-w-0 overflow-auto">{children}</section>
    </main>
  );
}

type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  badge?: string | null;
};

function NavGroup({ title, items, pathname }: { title: string; items: NavItem[]; pathname: string }) {
  return (
    <nav className="mb-8" aria-label={`${title} navigation`}>
      <p className="px-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#a8a8a3]">
        {title}
      </p>
      <div className="mt-3 space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.label}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex h-10 items-center gap-3 rounded-[10px] px-3 text-[13px] transition ${
                active ? "bg-brand-soft font-medium text-brand-dark" : "text-muted hover:bg-[#faf9f5] hover:text-ink"
              }`}
            >
              <span
                className={`grid size-[22px] place-items-center rounded-[6px] ${
                  active ? "bg-brand text-white" : "bg-[#efefeb]"
                }`}
              >
                <Icon size={13} />
              </span>
              <span>{item.label}</span>
              {item.badge ? (
                <span className="ml-auto rounded-full border border-line bg-[#efefeb] px-1.5 text-center font-mono text-[10px]">
                  {item.badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function initialsFor(name: string, email: string) {
  const source = name !== "Calendar user" ? name : email;
  const parts = source
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter(Boolean);
  return (parts[0]?.[0] ?? "C").toUpperCase() + (parts[1]?.[0] ?? parts[0]?.[1] ?? "U").toUpperCase();
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}
