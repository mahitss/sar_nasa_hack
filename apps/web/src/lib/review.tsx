"use client";

import { createContext, useContext, useSyncExternalStore } from "react";
import { evidenceItems } from "@/lib/evidence";

export type ReviewChoice = "accept" | "reject" | "needs-investigation";

const storageKey = "rivet-prototype-review";
let choices: Record<string, ReviewChoice | undefined> = {};
const listeners = new Set<() => void>();
let loaded = false;

function ensureLoaded() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  const stored = window.sessionStorage.getItem(storageKey);
  if (!stored) return;
  try {
    choices = JSON.parse(stored) as Record<string, ReviewChoice>;
  } catch {
    window.sessionStorage.removeItem(storageKey);
  }
}

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function snapshot() {
  ensureLoaded();
  return choices;
}

const ReviewContext = createContext<{
  choices: Record<string, ReviewChoice | undefined>;
  setChoice: (id: string, choice: ReviewChoice) => void;
} | null>(null);

export function ReviewProvider({ children }: { children: React.ReactNode }) {
  const current = useSyncExternalStore(subscribe, snapshot, () => choices);
  function setChoice(id: string, choice: ReviewChoice) {
    choices = { ...choices, [id]: choice };
    window.sessionStorage.setItem(storageKey, JSON.stringify(choices));
    emit();
  }
  return <ReviewContext.Provider value={{ choices: current, setChoice }}>{children}</ReviewContext.Provider>;
}

export function useReview() {
  const value = useContext(ReviewContext);
  if (!value) {
    return {
      choices: Object.fromEntries(evidenceItems.map((item) => [item.id, undefined])) as Record<string, ReviewChoice | undefined>,
      setChoice: () => undefined,
    };
  }
  return value;
}
