"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/** Load JSON from the API; re-runs when `path` changes. Pass null to skip. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!path) return;
    const n = ++seq.current;
    setLoading(true);
    try {
      const d = await api<T>(path);
      if (n === seq.current) { setData(d); setError(null); setErrorStatus(null); }
    } catch (e) {
      const err = e as { message: string; status?: number };
      if (n === seq.current) { setError(err.message); setErrorStatus(err.status ?? null); }
    } finally {
      if (n === seq.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => { load(); }, [load]);
  return { data, error, errorStatus, loading, reload: load, setData };
}
