"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical, Home, Settings, Shovel, Sprout, TestTube, Tractor, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/treatments", label: "Treatments", icon: FlaskConical },
  { href: "/cultural", label: "Cultural", icon: Shovel },
  { href: "/equipment", label: "Equipment", icon: Wrench },
  { href: "/products", label: "Products", icon: Sprout },
  { href: "/soil-tests", label: "Soil Tests", icon: TestTube },
  { href: "/zones", label: "Zones", icon: Tractor },
  { href: "/settings", label: "Settings", icon: Settings },
];

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div>
            <p className="text-sm font-semibold">Lawn Command Center</p>
            <p className="text-xs text-muted-foreground">Phase 1</p>
          </div>
          <p className="text-xs text-muted-foreground">Topeka, KS</p>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-1 md:grid-cols-[220px_1fr]">
        <aside className="hidden border-r p-3 md:block">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="min-h-[calc(100vh-3.5rem)] p-4 pb-20 md:p-6 md:pb-6">{children}</main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t bg-background md:hidden">
        <div className="grid grid-cols-4">
          {navItems.slice(0, 4).map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-1 px-2 py-2 text-[11px]",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}