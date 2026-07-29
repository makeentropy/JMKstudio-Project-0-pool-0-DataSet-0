export enum Permission {
  NONE = 0,
  READ = 1 << 0,
  WRITE = 1 << 1,
  DELETE = 1 << 2,
  CREATE = 1 << 3,
  UPDATE = 1 << 4,
  EXECUTE = 1 << 5,
  ADMIN = 1 << 6,
  SUPER_ADMIN = 1 << 7,

  READ_WRITE = READ | WRITE,
  FULL = READ | WRITE | DELETE | CREATE | UPDATE | EXECUTE,
  ALL = FULL | ADMIN | SUPER_ADMIN,
}

export enum ResourceType {
  USER = 'USER',
  ROLE = 'ROLE',
  CERTIFICATE = 'CERTIFICATE',
  PAYMENT = 'PAYMENT',
  ORDER = 'ORDER',
  SETTINGS = 'SETTINGS',
  REPORT = 'REPORT',
  LOG = 'LOG',
  API_KEY = 'API_KEY',
  GENERAL = 'GENERAL',
}

export enum AccessDecision {
  ALLOW = 'ALLOW',
  DENY = 'DENY',
  ABSTAIN = 'ABSTAIN',
}

export enum AuthProvider {
  LOCAL = 'LOCAL',
  LDAP = 'LDAP',
  OAUTH2 = 'OAUTH2',
  SAML = 'SAML',
  CERTIFICATE = 'CERTIFICATE',
}

export interface User {
  id: string;
  username: string;
  email: string;
  displayName?: string;
  passwordHash: string;
  passwordSalt: string;
  roles: string[];
  permissions: Permission;
  provider: AuthProvider;
  isActive: boolean;
  isLocked: boolean;
  lockUntil?: Date;
  failedLoginAttempts: number;
  lastLoginAt?: Date;
  lastLoginIp?: string;
  passwordChangedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, unknown>;
}

export interface PublicUser {
  id: string;
  username: string;
  email: string;
  displayName?: string;
  roles: string[];
  permissions: Permission;
  isActive: boolean;
  isLocked: boolean;
  lastLoginAt?: Date;
  createdAt: Date;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission;
  parentRoleId?: string;
  isSystem: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Resource {
  id: string;
  name: string;
  type: ResourceType;
  ownerId?: string;
  description?: string;
  attributes?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export interface AccessPolicy {
  id: string;
  name: string;
  description?: string;
  effect: AccessDecision;
  principalType: 'USER' | 'ROLE';
  principalIds: string[];
  resourceType?: ResourceType;
  resourceIds?: string[];
  permissions: Permission;
  priority: number;
  isActive: boolean;
  conditions?: PolicyCondition[];
  createdAt: Date;
  updatedAt: Date;
}

export interface PolicyCondition {
  type: 'ATTRIBUTE' | 'TIME' | 'IP' | 'CUSTOM';
  field?: string;
  operator: 'EQ' | 'NE' | 'GT' | 'LT' | 'GTE' | 'LTE' | 'IN' | 'NOT_IN' | 'CONTAINS';
  value: unknown;
}

export interface Session {
  id: string;
  userId: string;
  createdAt: Date;
  expiresAt: Date;
  lastActivityAt: Date;
  ipAddress?: string;
  userAgent?: string;
  isActive: boolean;
}

export class AuthError extends Error {
  public readonly code: string;
  public readonly cause?: unknown;

  constructor(message: string, code: string = 'AUTH_ERROR', cause?: unknown) {
    super(message);
    this.name = 'AuthError';
    this.code = code;
    this.cause = cause;
    Object.setPrototypeOf(this, AuthError.prototype);
  }
}

export class AuthenticationError extends AuthError {
  constructor(message: string, cause?: unknown) {
    super(message, 'AUTHENTICATION_FAILED', cause);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

export class PermissionError extends AuthError {
  constructor(message: string, cause?: unknown) {
    super(message, 'PERMISSION_DENIED', cause);
    this.name = 'PermissionError';
    Object.setPrototypeOf(this, PermissionError.prototype);
  }
}

export class SessionError extends AuthError {
  constructor(message: string, cause?: unknown) {
    super(message, 'SESSION_ERROR', cause);
    this.name = 'SessionError';
    Object.setPrototypeOf(this, SessionError.prototype);
  }
}

export class AccountLockedError extends AuthError {
  public readonly lockUntil?: Date;

  constructor(message: string, lockUntil?: Date, cause?: unknown) {
    super(message, 'ACCOUNT_LOCKED', cause);
    this.name = 'AccountLockedError';
    this.lockUntil = lockUntil;
    Object.setPrototypeOf(this, AccountLockedError.prototype);
  }
}

export class PolicyEvaluationResult {
  constructor(
    public readonly decision: AccessDecision,
    public readonly policyId?: string,
    public readonly reason?: string
  ) {}

  public get isAllowed(): boolean {
    return this.decision === AccessDecision.ALLOW;
  }

  public get isDenied(): boolean {
    return this.decision === AccessDecision.DENY;
  }
}

export const hasPermission = (userPerms: Permission, required: Permission): boolean => {
  if ((required & Permission.SUPER_ADMIN) !== 0 && (userPerms & Permission.SUPER_ADMIN) !== 0) {
    return true;
  }
  if ((required & Permission.ADMIN) !== 0 && (userPerms & Permission.ADMIN) !== 0) {
    return true;
  }
  return (userPerms & required) === required;
};

export const combinePermissions = (...perms: Permission[]): Permission => {
  return perms.reduce((acc, p) => acc | p, Permission.NONE);
};

export const removePermission = (base: Permission, toRemove: Permission): Permission => {
  return base & ~toRemove;
};

export const permissionNames: Record<Permission, string> = {
  [Permission.NONE]: 'NONE',
  [Permission.READ]: 'READ',
  [Permission.WRITE]: 'WRITE',
  [Permission.DELETE]: 'DELETE',
  [Permission.CREATE]: 'CREATE',
  [Permission.UPDATE]: 'UPDATE',
  [Permission.EXECUTE]: 'EXECUTE',
  [Permission.ADMIN]: 'ADMIN',
  [Permission.SUPER_ADMIN]: 'SUPER_ADMIN',
  [Permission.READ_WRITE]: 'READ_WRITE',
  [Permission.FULL]: 'FULL',
  [Permission.ALL]: 'ALL',
};

export const parsePermissions = (permValue: number): Permission[] => {
  const result: Permission[] = [];
  const allSingle: Permission[] = [
    Permission.READ,
    Permission.WRITE,
    Permission.DELETE,
    Permission.CREATE,
    Permission.UPDATE,
    Permission.EXECUTE,
    Permission.ADMIN,
    Permission.SUPER_ADMIN,
  ];
  for (const p of allSingle) {
    if ((permValue & p) !== 0) {
      result.push(p);
    }
  }
  return result;
};
