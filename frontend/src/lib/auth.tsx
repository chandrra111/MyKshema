"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, session } from "./api";
import type { Role, User } from "./types";

interface AuthCtx {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(session.user<User>());
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<{ access_token: string; user: User }>("/api/auth/demo-login", { body: { email, password } });
    session.save(res.access_token, res.user);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    session.clear();
    setUser(null);
    window.location.href = "/login";
  }, []);

  const refresh = useCallback(async () => {
    const me = await api<User>("/api/auth/me");
    const token = session.token();
    if (token) session.save(token, me);
    setUser(me);
  }, []);

  return <Ctx.Provider value={{ user, ready, login, logout, refresh }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}

/** Redirects to /login unless signed in with the given role. */
export function useRequireRole(role: Role) {
  const { user, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
    else if (user.role !== role) router.replace(user.role === "doctor" ? "/doctor" : "/patient");
  }, [ready, user, role, router]);
  return { user: user && user.role === role ? user : null, ready };
}
