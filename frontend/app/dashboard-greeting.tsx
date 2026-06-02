"use client";

import { useEffect, useState } from "react";

import { getTimeGreeting } from "@/lib/dashboard-ui";

export function DashboardGreeting({ userName }: { userName: string }) {
  const [greeting, setGreeting] = useState(() => getTimeGreeting(new Date().getHours()));

  useEffect(() => {
    function updateGreeting() {
      setGreeting(getTimeGreeting(new Date().getHours()));
    }

    updateGreeting();
    const timer = window.setInterval(updateGreeting, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <h1 className="text-xl font-semibold text-ink">
      {greeting}, {userName}
    </h1>
  );
}
