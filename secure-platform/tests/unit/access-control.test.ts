import * as crypto from 'crypto';

interface Role {
  id: string;
  name: string;
  permissions: string[];
}

interface User {
  id: string;
  username: string;
  passwordHash: string;
  passwordSalt: string;
  roles: string[];
  locked: boolean;
  loginAttempts: number;
  lockedUntil: number | null;
}

interface PolicyCondition {
  type: 'time_range';
  startHour: number;
  endHour: number;
  timezone?: string;
}

interface Policy {
  id: string;
  effect: 'allow' | 'deny';
  actions: string[];
  resources: string[];
  conditions?: PolicyCondition[];
}

interface AccessControlState {
  roles: Map<string, Role>;
  users: Map<string, User>;
  policies: Map<string, Policy>;
  roleAssignments: Map<string, string[]>;
  maxLoginAttempts: number;
  lockDurationMs: number;
}

const PBKDF2_ITERATIONS = 10000;
const PBKDF2_KEYLEN = 32;

const hashPassword = (password: string, salt: string): string => {
  return crypto
    .pbkdf2Sync(password, Buffer.from(salt, 'hex'), PBKDF2_ITERATIONS, PBKDF2_KEYLEN, 'sha256')
    .toString('hex');
};

const createSalt = (): string => crypto.randomBytes(16).toString('hex');

const ac: AccessControlState = {
  roles: new Map(),
  users: new Map(),
  policies: new Map(),
  roleAssignments: new Map(),
  maxLoginAttempts: 5,
  lockDurationMs: 15 * 60 * 1000,
};

const resetAC = (): void => {
  ac.roles.clear();
  ac.users.clear();
  ac.policies.clear();
  ac.roleAssignments.clear();
};

const createRole = (id: string, name: string, permissions: string[]): Role => {
  const role: Role = { id, name, permissions };
  ac.roles.set(id, role);
  return role;
};

const createUser = (
  username: string,
  plainPassword: string,
  roleIds: string[] = []
): User => {
  const salt = createSalt();
  const user: User = {
    id: crypto.randomBytes(12).toString('hex'),
    username,
    passwordSalt: salt,
    passwordHash: hashPassword(plainPassword, salt),
    roles: [...roleIds],
    locked: false,
    loginAttempts: 0,
    lockedUntil: null,
  };
  ac.users.set(user.id, user);
  ac.roleAssignments.set(user.id, [...roleIds]);
  return user;
};

const getUserByUsername = (username: string): User | undefined => {
  for (const user of ac.users.values()) {
    if (user.username === username) return user;
  }
  return undefined;
};

const gatherUserPermissions = (userId: string): Set<string> => {
  const perms = new Set<string>();
  const roleIds = ac.roleAssignments.get(userId) || [];
  for (const rid of roleIds) {
    const role = ac.roles.get(rid);
    if (role) role.permissions.forEach((p) => perms.add(p));
  }
  return perms;
};

const matchWildcard = (pattern: string, value: string): boolean => {
  if (pattern === '*') return true;
  if (pattern === value) return true;
  if (pattern.endsWith('/*')) {
    const prefix = pattern.slice(0, -2);
    return value === prefix || value.startsWith(prefix + '/');
  }
  if (pattern.endsWith(':*')) {
    const prefix = pattern.slice(0, -2);
    return value.startsWith(prefix + ':');
  }
  return false;
};

const checkAccess = (
  userId: string,
  action: string,
  resource: string,
  context: Record<string, unknown> = {}
): boolean => {
  const user = ac.users.get(userId);
  if (!user) return false;
  if (user.locked) return false;
  if (user.lockedUntil && user.lockedUntil > Date.now()) return false;

  const perms = gatherUserPermissions(userId);
  const genericAction = action.split(':')[0] + ':*';
  const genericResource = resource.split('/').slice(0, 2).join('/') + '/*';

  const directMatch = perms.has(`${action}:${resource}`);
  const actionWildcard = perms.has(`${genericAction}:${resource}`);
  const resourceWildcard = perms.has(`${action}:${genericResource}`);
  const doubleWildcard = perms.has(`${genericAction}:${genericResource}`);
  const adminWildcard = perms.has('*:*');

  if (!(directMatch || actionWildcard || resourceWildcard || doubleWildcard || adminWildcard)) {
    return false;
  }

  for (const policy of ac.policies.values()) {
    const actionMatch = policy.actions.some(a => matchWildcard(a, action));
    const resourceMatch = policy.resources.some(r => matchWildcard(r, resource));
    if (!actionMatch || !resourceMatch) continue;

    let conditionsPass = true;
    if (policy.conditions && policy.conditions.length) {
      for (const cond of policy.conditions) {
        if (cond.type === 'time_range') {
          const now = context.now instanceof Date ? context.now : new Date();
          const hour = (now as Date).getHours();
          if (hour < cond.startHour || hour >= cond.endHour) {
            conditionsPass = false;
            break;
          }
        }
      }
    }

    if (conditionsPass && policy.effect === 'deny') return false;
    if (!conditionsPass && policy.effect === 'allow') return false;
  }
  return true;
};

const login = (username: string, password: string): { success: boolean; userId?: string; reason?: string } => {
  const user = getUserByUsername(username);
  if (!user) return { success: false, reason: 'INVALID_CREDENTIALS' };

  if (user.lockedUntil && user.lockedUntil > Date.now()) {
    return { success: false, reason: 'ACCOUNT_LOCKED' };
  }
  if (user.locked) {
    return { success: false, reason: 'ACCOUNT_LOCKED' };
  }

  const computedHash = hashPassword(password, user.passwordSalt);
  if (computedHash !== user.passwordHash) {
    user.loginAttempts += 1;
    if (user.loginAttempts >= ac.maxLoginAttempts) {
      user.lockedUntil = Date.now() + ac.lockDurationMs;
      user.loginAttempts = 0;
      return { success: false, reason: 'ACCOUNT_LOCKED' };
    }
    return { success: false, reason: 'INVALID_CREDENTIALS' };
  }

  user.loginAttempts = 0;
  user.lockedUntil = null;
  return { success: true, userId: user.id };
};

const changePassword = (
  userId: string,
  oldPassword: string,
  newPassword: string
): { success: boolean; reason?: string } => {
  const user = ac.users.get(userId);
  if (!user) return { success: false, reason: 'USER_NOT_FOUND' };

  const oldHash = hashPassword(oldPassword, user.passwordSalt);
  if (oldHash !== user.passwordHash) {
    return { success: false, reason: 'OLD_PASSWORD_INCORRECT' };
  }

  const newSalt = createSalt();
  user.passwordSalt = newSalt;
  user.passwordHash = hashPassword(newPassword, newSalt);
  return { success: true };
};

const evaluatePolicy = (
  policy: Policy,
  context: Record<string, unknown> = {}
): { allowed: boolean; reason?: string } => {
  if (!policy.conditions || policy.conditions.length === 0) {
    return { allowed: policy.effect === 'allow' };
  }

  for (const cond of policy.conditions) {
    if (cond.type === 'time_range') {
      const now = context.now instanceof Date ? (context.now as Date) : new Date();
      const hour = now.getHours();
      if (hour < cond.startHour || hour >= cond.endHour) {
        return {
          allowed: policy.effect === 'allow' ? false : true,
          reason: 'TIME_RANGE_VIOLATION',
        };
      }
    }
  }
  return { allowed: policy.effect === 'allow' };
};

describe('Access Control', () => {
  beforeEach(() => {
    resetAC();
  });

  describe('Role & Permission based access (2 users, 2 roles, 10 cases)', () => {
    let adminRole: Role;
    let userRole: Role;
    let alice: User;
    let bob: User;

    beforeEach(() => {
      adminRole = createRole('r_admin', 'Administrator', [
        'read:users/all',
        'write:users/all',
        'delete:users/all',
        'read:orders/all',
        'write:orders/all',
        'read:system/config',
        'write:system/config',
        'read:payments/all',
        'write:payments/all',
        '*:*',
      ]);
      userRole = createRole('r_user', 'Regular User', [
        'read:users/self',
        'write:users/self',
        'read:orders/self',
        'write:orders/self',
        'read:profile/self',
        'write:profile/self',
      ]);
      alice = createUser('alice', 'AlicePass123!', ['r_admin']);
      bob = createUser('bob', 'BobPass456!', ['r_user']);
    });

    it('covers 10 checkAccess forward/reverse cases', () => {
      const cases: Array<{
        name: string;
        userId: string;
        action: string;
        resource: string;
        expected: boolean;
      }> = [
        { name: '[正向] admin读取所有用户', userId: alice.id, action: 'read', resource: 'users/all', expected: true },
        { name: '[正向] admin删除用户', userId: alice.id, action: 'delete', resource: 'users/all', expected: true },
        { name: '[正向] admin写系统配置', userId: alice.id, action: 'write', resource: 'system/config', expected: true },
        { name: '[正向] admin读全部支付', userId: alice.id, action: 'read', resource: 'payments/all', expected: true },
        { name: '[正向] user读自己profile', userId: bob.id, action: 'read', resource: 'profile/self', expected: true },
        { name: '[正向] user写自己订单', userId: bob.id, action: 'write', resource: 'orders/self', expected: true },
        { name: '[反向] user不能读全部用户', userId: bob.id, action: 'read', resource: 'users/all', expected: false },
        { name: '[反向] user不能写系统配置', userId: bob.id, action: 'write', resource: 'system/config', expected: false },
        { name: '[反向] user不能删除任何用户', userId: bob.id, action: 'delete', resource: 'users/all', expected: false },
        { name: '[反向] 不存在用户拒绝访问', userId: 'non-existent-id', action: 'read', resource: 'profile/self', expected: false },
      ];

      expect.assertions(cases.length);
      for (const tc of cases) {
        expect(checkAccess(tc.userId, tc.action, tc.resource)).toBe(tc.expected);
      }
    });

    it('additional wildcard & multi-action checks', () => {
      expect(checkAccess(alice.id, 'execute', 'jobs/nightly')).toBe(true);
      expect(checkAccess(alice.id, 'approve', 'loans/123')).toBe(true);
      expect(checkAccess(bob.id, 'execute', 'jobs/nightly')).toBe(false);
    });
  });

  describe('Login failure lockout (5 failures)', () => {
    let user: User;

    beforeEach(() => {
      createRole('r_basic', 'Basic', ['read:data/*']);
      user = createUser('lockuser', 'CorrectSecret-2024', ['r_basic']);
    });

    it('locks after 5 consecutive failures', () => {
      for (let i = 1; i <= 4; i++) {
        const r = login('lockuser', 'wrong-password-' + i);
        expect(r.success).toBe(false);
        expect(r.reason).toBe('INVALID_CREDENTIALS');
      }

      const fresh = ac.users.get(user.id)!;
      expect(fresh.loginAttempts).toBe(4);
      expect(fresh.lockedUntil).toBeNull();

      const fifth = login('lockuser', 'definitely-wrong');
      expect(fifth.success).toBe(false);
      expect(fifth.reason).toBe('ACCOUNT_LOCKED');

      const afterLock = ac.users.get(user.id)!;
      expect(afterLock.lockedUntil).not.toBeNull();
      expect(afterLock.lockedUntil!).toBeGreaterThan(Date.now());

      const correctNow = login('lockuser', 'CorrectSecret-2024');
      expect(correctNow.success).toBe(false);
      expect(correctNow.reason).toBe('ACCOUNT_LOCKED');
    });

    it('success resets failure counter', () => {
      login('lockuser', 'wrong1');
      login('lockuser', 'wrong2');
      const u = ac.users.get(user.id)!;
      expect(u.loginAttempts).toBe(2);

      const ok = login('lockuser', 'CorrectSecret-2024');
      expect(ok.success).toBe(true);
      const u2 = ac.users.get(user.id)!;
      expect(u2.loginAttempts).toBe(0);
      expect(u2.lockedUntil).toBeNull();
    });
  });

  describe('Password change - old password incorrect', () => {
    let user: User;

    beforeEach(() => {
      createRole('r_guest', 'Guest', []);
      user = createUser('changeme', 'OldSecurePwd@123', ['r_guest']);
    });

    it('rejects change when old password is wrong', () => {
      const result = changePassword(user.id, 'WrongOldPwd!', 'NewSecurePwd@456');
      expect(result.success).toBe(false);
      expect(result.reason).toBe('OLD_PASSWORD_INCORRECT');

      const verifyStillOld = login('changeme', 'OldSecurePwd@123');
      expect(verifyStillOld.success).toBe(true);

      const verifyNewFails = login('changeme', 'NewSecurePwd@456');
      expect(verifyNewFails.success).toBe(false);
    });

    it('succeeds when old password is correct', () => {
      const result = changePassword(user.id, 'OldSecurePwd@123', 'NewSecurePwd@456');
      expect(result.success).toBe(true);
      expect(result.reason).toBeUndefined();

      expect(login('changeme', 'OldSecurePwd@123').success).toBe(false);
      expect(login('changeme', 'NewSecurePwd@456').success).toBe(true);
    });

    it('returns USER_NOT_FOUND for invalid userId', () => {
      const r = changePassword('fake-id', 'x', 'y');
      expect(r.success).toBe(false);
      expect(r.reason).toBe('USER_NOT_FOUND');
    });
  });

  describe('Policy evaluate with time_range conditions (9-18)', () => {
    let allowPolicy: Policy;
    let denyPolicy: Policy;

    beforeEach(() => {
      allowPolicy = {
        id: 'p_allow_business',
        effect: 'allow',
        actions: ['read', 'write'],
        resources: ['documents/*'],
        conditions: [{ type: 'time_range', startHour: 9, endHour: 18 }],
      };
      denyPolicy = {
        id: 'p_deny_afterhours',
        effect: 'deny',
        actions: ['delete'],
        resources: ['documents/*'],
        conditions: [{ type: 'time_range', startHour: 9, endHour: 18 }],
      };
      ac.policies.set(allowPolicy.id, allowPolicy);
      ac.policies.set(denyPolicy.id, denyPolicy);

      createRole('r_staff', 'Staff', ['read:documents/*', 'write:documents/*']);
    });

    const mkDate = (hour: number): Date => {
      const d = new Date('2024-06-15T12:00:00Z');
      d.setHours(hour, 0, 0, 0);
      return d;
    };

    it('evaluate allows during business hours (9-18)', () => {
      const cases = [9, 10, 12, 14, 17, 17, 17];
      for (const h of cases) {
        const r = evaluatePolicy(allowPolicy, { now: mkDate(h) });
        expect(r.allowed).toBe(true);
      }
    });

    it('evaluate rejects outside business hours', () => {
      const outside = [0, 6, 8, 18, 19, 22, 23];
      for (const h of outside) {
        const r = evaluatePolicy(allowPolicy, { now: mkDate(h) });
        expect(r.allowed).toBe(false);
        expect(r.reason).toBe('TIME_RANGE_VIOLATION');
      }
    });

    it('checkAccess enforces time_range: admin write at 3am denied if policy requires 9-18', () => {
      const staffRole = createRole('r_doc_writer', 'DocWriter', ['write:documents/reports']);
      const staff = createUser('staff1', 'Staff-2024', ['r_doc_writer']);

      const workingTime = mkDate(11);
      expect(checkAccess(staff.id, 'write', 'documents/reports', { now: workingTime })).toBe(true);

      const weeHours = mkDate(3);
      expect(checkAccess(staff.id, 'write', 'documents/reports', { now: weeHours })).toBe(false);
    });

    it('policy without conditions: evaluate always applies effect', () => {
      const simpleAllow: Policy = {
        id: 'simple', effect: 'allow', actions: ['*'], resources: ['*'],
      };
      expect(evaluatePolicy(simpleAllow, { now: mkDate(2) }).allowed).toBe(true);
      const simpleDeny: Policy = {
        id: 'simple2', effect: 'deny', actions: ['*'], resources: ['*'],
      };
      expect(evaluatePolicy(simpleDeny, { now: mkDate(12) }).allowed).toBe(false);
    });

    it('deny policy during working hours: delete blocked 9-18, allowed other times', () => {
      for (let h = 9; h < 18; h++) {
        const r = evaluatePolicy(denyPolicy, { now: mkDate(h) });
        expect(r.allowed).toBe(false);
      }
      const r = evaluatePolicy(denyPolicy, { now: mkDate(20) });
      expect(r.allowed).toBe(true);
      expect(r.reason).toBe('TIME_RANGE_VIOLATION');
    });
  });
});
