"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center">
      <span className="text-xs font-mono font-bold text-[#0C2B4E]">Loading Healysis Network...</span>
    </div>
  );
}