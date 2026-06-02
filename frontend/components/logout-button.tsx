"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { supabaseBrowserClient } from "@/lib/supabase/client";

export function LogoutButton({
  variant = "icon",
  className = "",
}: {
  variant?: "icon" | "menu";
  className?: string;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function logout() {
    startTransition(async () => {
      await supabaseBrowserClient.auth.signOut();
      router.push("/login");
      router.refresh();
    });
  }

  if (variant === "menu") {
    return (
      <button
        type="button"
        onClick={logout}
        disabled={isPending}
        className={`flex h-9 w-full items-center justify-center gap-2 rounded-[10px] border border-line bg-[#efefeb] px-3 text-xs font-medium text-ink hover:bg-white disabled:opacity-50 ${className}`}
      >
        <LogOut size={14} />
        {isPending ? "Signing out..." : "Log out"}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={logout}
      disabled={isPending}
      className={`grid size-8 place-items-center rounded-[10px] border border-line bg-[#efefeb] text-muted disabled:opacity-50 ${className}`}
      title="Log out"
    >
      <LogOut size={14} />
    </button>
  );
}
