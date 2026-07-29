import { pbkdf2Sync, randomBytes, timingSafeEqual } from 'node:crypto';
import { v4 as uuidv4 } from 'uuid';
import {
  User,
  PublicUser,
  Session,
  AuthProvider,
  Permission,
  AuthError,
  AuthenticationError,
  AccountLockedError,
  SessionError,
  hasPermission,
} from './types';

const PBKDF2_ITERATIONS = 600000;
const PBKDF2_KEYLEN = 64;
const PBKDF2_DIGEST = 'sha256';
const SALT_BYTES = 32;
const MAX_FAILED_ATTEMPTS = 5;
const LOCK_DURATION_MS = 60 * 60 * 1000;
const DEFAULT_SESSION_TTL_MS = 86400 * 1000;

export class UserManager {
  private users: Map<string, User> = new Map();
  private usernameIndex: Map<string, string> = new Map();
  private emailIndex: Map<string, string> = new Map();
  private sessions: Map<string, Session> = new Map();
  private userSessions: Map<string, Set<string>> = new Map();

  public createUser(params: {
    username: string;
    email: string;
    password: string;
    displayName?: string;
    roles?: string[];
    permissions?: Permission;
    provider?: AuthProvider;
    metadata?: Record<string, unknown>;
  }): PublicUser {
    const { username, email, password, displayName, roles = [], permissions = Permission.NONE, provider = AuthProvider.LOCAL, metadata } = params;

    if (!username || username.length < 3) {
      throw new AuthError('用户名至少需要3个字符', 'INVALID_USERNAME');
    }
    if (!email || !this.isValidEmail(email)) {
      throw new AuthError('邮箱格式无效', 'INVALID_EMAIL');
    }
    if (!password || password.length < 8) {
      throw new AuthError('密码至少需要8个字符', 'INVALID_PASSWORD');
    }

    const normalizedUsername = username.toLowerCase();
    const normalizedEmail = email.toLowerCase();

    if (this.usernameIndex.has(normalizedUsername)) {
      throw new AuthError(`用户名已存在: ${username}`, 'USERNAME_EXISTS');
    }
    if (this.emailIndex.has(normalizedEmail)) {
      throw new AuthError(`邮箱已存在: ${email}`, 'EMAIL_EXISTS');
    }

    const salt = randomBytes(SALT_BYTES).toString('hex');
    const passwordHash = this.hashPassword(password, salt);
    const now = new Date();

    const user: User = {
      id: uuidv4(),
      username,
      email,
      displayName,
      passwordHash,
      passwordSalt: salt,
      roles,
      permissions,
      provider,
      isActive: true,
      isLocked: false,
      failedLoginAttempts: 0,
      createdAt: now,
      updatedAt: now,
      metadata,
    };

    this.users.set(user.id, user);
    this.usernameIndex.set(normalizedUsername, user.id);
    this.emailIndex.set(normalizedEmail, user.id);

    return this.toPublicUser(user);
  }

  public authenticate(
    usernameOrEmail: string,
    password: string,
    ipAddress?: string,
    userAgent?: string
  ): { user: PublicUser; session: Session } {
    const normalized = usernameOrEmail.toLowerCase();
    let userId = this.usernameIndex.get(normalized);
    if (!userId) {
      userId = this.emailIndex.get(normalized);
    }

    const genericError = new AuthenticationError('用户名或密码错误');

    if (!userId) {
      this.simulatePasswordVerify();
      throw genericError;
    }

    const user = this.users.get(userId)!;

    if (!user.isActive) {
      throw new AuthenticationError('账户已停用');
    }

    if (user.isLocked) {
      if (user.lockUntil && user.lockUntil > new Date()) {
        const remainingMinutes = Math.ceil((user.lockUntil.getTime() - Date.now()) / 60000);
        throw new AccountLockedError(
          `账户已锁定，请${remainingMinutes}分钟后再试`,
          user.lockUntil
        );
      }
      user.isLocked = false;
      user.lockUntil = undefined;
      user.failedLoginAttempts = 0;
    }

    const isValid = this.verifyPassword(password, user.passwordHash, user.passwordSalt);

    if (!isValid) {
      user.failedLoginAttempts++;
      if (user.failedLoginAttempts >= MAX_FAILED_ATTEMPTS) {
        user.isLocked = true;
        user.lockUntil = new Date(Date.now() + LOCK_DURATION_MS);
        user.updatedAt = new Date();
        throw new AccountLockedError(
          `登录失败次数过多，账户已锁定${LOCK_DURATION_MS / 3600000}小时`,
          user.lockUntil
        );
      }
      user.updatedAt = new Date();
      throw genericError;
    }

    user.failedLoginAttempts = 0;
    user.isLocked = false;
    user.lockUntil = undefined;
    user.lastLoginAt = new Date();
    user.lastLoginIp = ipAddress;
    user.updatedAt = new Date();

    const session = this.createSession(user.id, ipAddress, userAgent);

    return {
      user: this.toPublicUser(user),
      session,
    };
  }

  public logout(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return;
    }

    session.isActive = false;
    this.sessions.delete(sessionId);

    const userSessionSet = this.userSessions.get(session.userId);
    if (userSessionSet) {
      userSessionSet.delete(sessionId);
      if (userSessionSet.size === 0) {
        this.userSessions.delete(session.userId);
      }
    }
  }

  public logoutAll(userId: string): number {
    const userSessionSet = this.userSessions.get(userId);
    if (!userSessionSet) {
      return 0;
    }

    const count = userSessionSet.size;
    for (const sessionId of userSessionSet) {
      this.sessions.delete(sessionId);
    }
    this.userSessions.delete(userId);
    return count;
  }

  public validateSession(sessionId: string): PublicUser | null {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) {
      return null;
    }

    if (session.expiresAt < new Date()) {
      this.logout(sessionId);
      return null;
    }

    const user = this.users.get(session.userId);
    if (!user || !user.isActive) {
      this.logout(sessionId);
      return null;
    }

    session.lastActivityAt = new Date();
    return this.toPublicUser(user);
  }

  public getSession(sessionId: string): Session | null {
    return this.sessions.get(sessionId) ?? null;
  }

  public listUserSessions(userId: string): Session[] {
    const userSessionSet = this.userSessions.get(userId);
    if (!userSessionSet) return [];

    return Array.from(userSessionSet)
      .map(id => this.sessions.get(id))
      .filter((s): s is Session => s !== undefined)
      .sort((a, b) => b.lastActivityAt.getTime() - a.lastActivityAt.getTime());
  }

  public getUser(userId: string): PublicUser | null {
    const user = this.users.get(userId);
    return user ? this.toPublicUser(user) : null;
  }

  public getUserByUsername(username: string): PublicUser | null {
    const userId = this.usernameIndex.get(username.toLowerCase());
    return userId ? this.getUser(userId) : null;
  }

  public getFullUser(userId: string): User | null {
    return this.users.get(userId) ?? null;
  }

  public changePassword(
    userId: string,
    oldPassword: string,
    newPassword: string
  ): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    if (!this.verifyPassword(oldPassword, user.passwordHash, user.passwordSalt)) {
      throw new AuthenticationError('原密码错误');
    }

    if (newPassword.length < 8) {
      throw new AuthError('新密码至少需要8个字符', 'INVALID_PASSWORD');
    }

    if (this.verifyPassword(newPassword, user.passwordHash, user.passwordSalt)) {
      throw new AuthError('新密码不能与旧密码相同', 'PASSWORD_UNCHANGED');
    }

    const newSalt = randomBytes(SALT_BYTES).toString('hex');
    user.passwordHash = this.hashPassword(newPassword, newSalt);
    user.passwordSalt = newSalt;
    user.passwordChangedAt = new Date();
    user.updatedAt = new Date();
  }

  public adminResetPassword(userId: string, newPassword: string): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    if (newPassword.length < 8) {
      throw new AuthError('新密码至少需要8个字符', 'INVALID_PASSWORD');
    }

    const newSalt = randomBytes(SALT_BYTES).toString('hex');
    user.passwordHash = this.hashPassword(newPassword, newSalt);
    user.passwordSalt = newSalt;
    user.passwordChangedAt = new Date();
    user.updatedAt = new Date();

    this.logoutAll(userId);
  }

  public setUserActive(userId: string, active: boolean): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    user.isActive = active;
    user.updatedAt = new Date();

    if (!active) {
      this.logoutAll(userId);
    }
  }

  public unlockUser(userId: string): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    user.isLocked = false;
    user.lockUntil = undefined;
    user.failedLoginAttempts = 0;
    user.updatedAt = new Date();
  }

  public listUsers(params?: {
    includeInactive?: boolean;
    roleId?: string;
    search?: string;
  }): PublicUser[] {
    const { includeInactive = false, roleId, search } = params || {};
    const searchLower = search?.toLowerCase();

    return Array.from(this.users.values())
      .filter(user => includeInactive || user.isActive)
      .filter(user => !roleId || user.roles.includes(roleId))
      .filter(user => {
        if (!searchLower) return true;
        return (
          user.username.toLowerCase().includes(searchLower) ||
          user.email.toLowerCase().includes(searchLower) ||
          (user.displayName && user.displayName.toLowerCase().includes(searchLower))
        );
      })
      .map(user => this.toPublicUser(user))
      .sort((a, b) => a.username.localeCompare(b.username));
  }

  public assignRole(userId: string, roleId: string): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    if (!user.roles.includes(roleId)) {
      user.roles = [...user.roles, roleId];
      user.updatedAt = new Date();
    }
  }

  public revokeRole(userId: string, roleId: string): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    user.roles = user.roles.filter(r => r !== roleId);
    user.updatedAt = new Date();
  }

  public grantUserPermission(userId: string, permission: Permission): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    user.permissions = user.permissions | permission;
    user.updatedAt = new Date();
  }

  public revokeUserPermission(userId: string, permission: Permission): void {
    const user = this.users.get(userId);
    if (!user) {
      throw new AuthError('用户不存在', 'USER_NOT_FOUND');
    }

    user.permissions = user.permissions & ~permission;
    user.updatedAt = new Date();
  }

  public userHasPermission(userId: string, permission: Permission): boolean {
    const user = this.users.get(userId);
    if (!user) return false;
    return hasPermission(user.permissions, permission);
  }

  public refreshSession(sessionId: string): Session | null {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) return null;

    if (session.expiresAt < new Date()) {
      this.logout(sessionId);
      return null;
    }

    session.expiresAt = new Date(Date.now() + DEFAULT_SESSION_TTL_MS);
    session.lastActivityAt = new Date();
    return session;
  }

  public get userCount(): number {
    return this.users.size;
  }

  public get activeSessionCount(): number {
    return this.sessions.size;
  }

  private createSession(userId: string, ipAddress?: string, userAgent?: string): Session {
    const now = new Date();
    const sessionId = randomBytes(32).toString('hex');
    const session: Session = {
      id: sessionId,
      userId,
      createdAt: now,
      expiresAt: new Date(now.getTime() + DEFAULT_SESSION_TTL_MS),
      lastActivityAt: now,
      ipAddress,
      userAgent,
      isActive: true,
    };

    this.sessions.set(sessionId, session);

    if (!this.userSessions.has(userId)) {
      this.userSessions.set(userId, new Set());
    }
    this.userSessions.get(userId)!.add(sessionId);

    return session;
  }

  private hashPassword(password: string, salt: string): string {
    const derivedKey = pbkdf2Sync(
      password,
      salt,
      PBKDF2_ITERATIONS,
      PBKDF2_KEYLEN,
      PBKDF2_DIGEST
    );
    return derivedKey.toString('hex');
  }

  private verifyPassword(password: string, hash: string, salt: string): boolean {
    try {
      const derivedKey = pbkdf2Sync(
        password,
        salt,
        PBKDF2_ITERATIONS,
        PBKDF2_KEYLEN,
        PBKDF2_DIGEST
      );
      const hashBuf = Buffer.from(hash, 'hex');
      if (derivedKey.length !== hashBuf.length) {
        return false;
      }
      return timingSafeEqual(derivedKey, hashBuf);
    } catch {
      return false;
    }
  }

  private simulatePasswordVerify(): void {
    try {
      const dummySalt = randomBytes(SALT_BYTES).toString('hex');
      pbkdf2Sync('dummy', dummySalt, PBKDF2_ITERATIONS, PBKDF2_KEYLEN, PBKDF2_DIGEST);
    } catch {
      // ignore
    }
  }

  private isValidEmail(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  private toPublicUser(user: User): PublicUser {
    return {
      id: user.id,
      username: user.username,
      email: user.email,
      displayName: user.displayName,
      roles: [...user.roles],
      permissions: user.permissions,
      isActive: user.isActive,
      isLocked: user.isLocked,
      lastLoginAt: user.lastLoginAt,
      createdAt: user.createdAt,
    };
  }
}
