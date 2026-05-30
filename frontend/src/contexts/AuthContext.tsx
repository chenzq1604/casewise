/**
 * CaseWise 法律AI工具 - 用户认证上下文
 *
 * 提供全局用户状态管理、登录/登出、Token持久化等功能。
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, type UserInfo } from '../services/api';

interface AuthContextType {
  /** 当前用户信息，未登录时为null */
  user: UserInfo | null;
  /** JWT Token */
  token: string | null;
  /** 是否正在加载认证状态 */
  loading: boolean;
  /** 登录 */
  login: (username: string, password: string) => Promise<void>;
  /** 登出 */
  logout: () => void;
  /** 检查当前用户是否拥有指定角色 */
  hasRole: (...roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'casewise_token';
const USER_KEY = 'casewise_user';

/**
 * 认证上下文Provider组件
 *
 * 在App根节点包裹，提供全局认证状态。
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser = localStorage.getItem(USER_KEY);

    if (savedToken && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser) as UserInfo;
        setToken(savedToken);
        setUser(parsedUser);

        authApi.getMe(savedToken).then((freshUser) => {
          if (freshUser) {
            setUser(freshUser);
            localStorage.setItem(USER_KEY, JSON.stringify(freshUser));
          } else {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
            setToken(null);
            setUser(null);
          }
        }).catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setToken(null);
          setUser(null);
        }).finally(() => {
          setLoading(false);
        });
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const hasRole = useCallback((...roles: string[]) => {
    if (!user) return false;
    return roles.includes(user.role);
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * 使用认证上下文的Hook
 *
 * @returns AuthContextType
 * @throws 在AuthProvider外使用会抛出错误
 */
export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
};
