import { v4 as uuidv4 } from 'uuid';
import {
  Role,
  Resource,
  AccessPolicy,
  ResourceType,
  Permission,
  AccessDecision,
  PolicyEvaluationResult,
  AuthError,
  PermissionError,
  hasPermission,
  combinePermissions,
  PolicyCondition,
} from './types';
import { UserManager } from './user-manager';

export class RoleManager {
  private roles: Map<string, Role> = new Map();
  private roleNameIndex: Map<string, string> = new Map();

  public createRole(params: {
    name: string;
    description?: string;
    permissions?: Permission;
    parentRoleId?: string;
    isSystem?: boolean;
  }): Role {
    const { name, description, permissions = Permission.NONE, parentRoleId, isSystem = false } = params;

    if (!name || name.trim().length === 0) {
      throw new AuthError('角色名称不能为空', 'INVALID_ROLE_NAME');
    }

    const normalizedName = name.toLowerCase();
    if (this.roleNameIndex.has(normalizedName)) {
      throw new AuthError(`角色名称已存在: ${name}`, 'ROLE_NAME_EXISTS');
    }

    if (parentRoleId && !this.roles.has(parentRoleId)) {
      throw new AuthError(`父角色不存在: ${parentRoleId}`, 'PARENT_ROLE_NOT_FOUND');
    }

    const now = new Date();
    const role: Role = {
      id: uuidv4(),
      name,
      description,
      permissions,
      parentRoleId,
      isSystem,
      createdAt: now,
      updatedAt: now,
    };

    this.roles.set(role.id, role);
    this.roleNameIndex.set(normalizedName, role.id);

    return role;
  }

  public getRole(roleId: string): Role | null {
    return this.roles.get(roleId) ?? null;
  }

  public getRoleByName(name: string): Role | null {
    const id = this.roleNameIndex.get(name.toLowerCase());
    return id ? this.roles.get(id) ?? null : null;
  }

  public updateRole(roleId: string, updates: {
    name?: string;
    description?: string;
    permissions?: Permission;
    parentRoleId?: string | null;
  }): Role {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new AuthError(`角色不存在: ${roleId}`, 'ROLE_NOT_FOUND');
    }

    if (role.isSystem && (updates.name !== undefined || updates.parentRoleId !== undefined)) {
      throw new AuthError('系统角色不允许修改名称或父角色', 'SYSTEM_ROLE_IMMUTABLE');
    }

    if (updates.name !== undefined) {
      const newNormalized = updates.name.toLowerCase();
      const existingId = this.roleNameIndex.get(newNormalized);
      if (existingId && existingId !== roleId) {
        throw new AuthError(`角色名称已存在: ${updates.name}`, 'ROLE_NAME_EXISTS');
      }
      this.roleNameIndex.delete(role.name.toLowerCase());
      this.roleNameIndex.set(newNormalized, roleId);
      role.name = updates.name;
    }

    if (updates.description !== undefined) {
      role.description = updates.description;
    }

    if (updates.permissions !== undefined) {
      role.permissions = updates.permissions;
    }

    if (updates.parentRoleId !== undefined) {
      if (updates.parentRoleId === null) {
        role.parentRoleId = undefined;
      } else {
        if (!this.roles.has(updates.parentRoleId)) {
          throw new AuthError(`父角色不存在: ${updates.parentRoleId}`, 'PARENT_ROLE_NOT_FOUND');
        }
        if (this.wouldCreateCycle(roleId, updates.parentRoleId)) {
          throw new AuthError('父角色设置将导致循环继承', 'CYCLIC_INHERITANCE');
        }
        role.parentRoleId = updates.parentRoleId;
      }
    }

    role.updatedAt = new Date();
    return role;
  }

  public deleteRole(roleId: string): void {
    const role = this.roles.get(roleId);
    if (!role) return;

    if (role.isSystem) {
      throw new AuthError('系统角色不允许删除', 'SYSTEM_ROLE_IMMUTABLE');
    }

    for (const other of this.roles.values()) {
      if (other.parentRoleId === roleId) {
        other.parentRoleId = undefined;
        other.updatedAt = new Date();
      }
    }

    this.roleNameIndex.delete(role.name.toLowerCase());
    this.roles.delete(roleId);
  }

  public listRoles(): Role[] {
    return Array.from(this.roles.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  public grantPermission(roleId: string, permission: Permission): Role {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new AuthError(`角色不存在: ${roleId}`, 'ROLE_NOT_FOUND');
    }
    role.permissions = role.permissions | permission;
    role.updatedAt = new Date();
    return role;
  }

  public revokePermission(roleId: string, permission: Permission): Role {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new AuthError(`角色不存在: ${roleId}`, 'ROLE_NOT_FOUND');
    }
    role.permissions = role.permissions & ~permission;
    role.updatedAt = new Date();
    return role;
  }

  public getEffectivePermissions(roleId: string): Permission {
    const visited = new Set<string>();
    let current: string | undefined = roleId;
    let perms = Permission.NONE;

    while (current && !visited.has(current)) {
      visited.add(current);
      const role = this.roles.get(current);
      if (!role) break;
      perms = perms | role.permissions;
      current = role.parentRoleId;
    }

    return perms;
  }

  public getRoleHierarchy(roleId: string): Role[] {
    const result: Role[] = [];
    const visited = new Set<string>();
    let current: string | undefined = roleId;

    while (current && !visited.has(current)) {
      visited.add(current);
      const role = this.roles.get(current);
      if (!role) break;
      result.push(role);
      current = role.parentRoleId;
    }

    return result;
  }

  private wouldCreateCycle(childId: string, newParentId: string): boolean {
    let current: string | undefined = newParentId;
    const visited = new Set<string>();

    while (current && !visited.has(current)) {
      if (current === childId) return true;
      visited.add(current);
      const role = this.roles.get(current);
      if (!role) break;
      current = role.parentRoleId;
    }

    return false;
  }
}

export class ResourceManager {
  private resources: Map<string, Resource> = new Map();

  public createResource(params: {
    name: string;
    type: ResourceType;
    ownerId?: string;
    description?: string;
    attributes?: Record<string, unknown>;
  }): Resource {
    const { name, type, ownerId, description, attributes } = params;

    if (!name || name.trim().length === 0) {
      throw new AuthError('资源名称不能为空', 'INVALID_RESOURCE_NAME');
    }

    const now = new Date();
    const resource: Resource = {
      id: uuidv4(),
      name,
      type,
      ownerId,
      description,
      attributes,
      createdAt: now,
      updatedAt: now,
    };

    this.resources.set(resource.id, resource);
    return resource;
  }

  public getResource(resourceId: string): Resource | null {
    return this.resources.get(resourceId) ?? null;
  }

  public updateResource(resourceId: string, updates: {
    name?: string;
    description?: string;
    attributes?: Record<string, unknown>;
  }): Resource {
    const resource = this.resources.get(resourceId);
    if (!resource) {
      throw new AuthError(`资源不存在: ${resourceId}`, 'RESOURCE_NOT_FOUND');
    }

    if (updates.name !== undefined) resource.name = updates.name;
    if (updates.description !== undefined) resource.description = updates.description;
    if (updates.attributes !== undefined) {
      resource.attributes = { ...resource.attributes, ...updates.attributes };
    }
    resource.updatedAt = new Date();
    return resource;
  }

  public deleteResource(resourceId: string): void {
    this.resources.delete(resourceId);
  }

  public listResources(params?: {
    type?: ResourceType;
    ownerId?: string;
  }): Resource[] {
    return Array.from(this.resources.values())
      .filter(r => !params?.type || r.type === params.type)
      .filter(r => !params?.ownerId || r.ownerId === params.ownerId)
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  public setOwner(resourceId: string, ownerId: string): void {
    const resource = this.resources.get(resourceId);
    if (!resource) {
      throw new AuthError(`资源不存在: ${resourceId}`, 'RESOURCE_NOT_FOUND');
    }
    resource.ownerId = ownerId;
    resource.updatedAt = new Date();
  }
}

export class AccessController {
  private userManager: UserManager;
  private roleManager: RoleManager;
  private resourceManager: ResourceManager;
  private policies: Map<string, AccessPolicy> = new Map();

  constructor(
    userManager: UserManager,
    roleManager?: RoleManager,
    resourceManager?: ResourceManager
  ) {
    this.userManager = userManager;
    this.roleManager = roleManager || new RoleManager();
    this.resourceManager = resourceManager || new ResourceManager();
  }

  public get userManager_(): UserManager {
    return this.userManager;
  }

  public get roleManager_(): RoleManager {
    return this.roleManager;
  }

  public get resourceManager_(): ResourceManager {
    return this.resourceManager;
  }

  public getUserEffectivePermissions(userId: string): Permission {
    const user = this.userManager.getFullUser(userId);
    if (!user) return Permission.NONE;

    let perms = user.permissions;

    for (const roleId of user.roles) {
      perms = perms | this.roleManager.getEffectivePermissions(roleId);
    }

    return perms;
  }

  public checkAccess(
    userId: string,
    resourceId: string,
    permission: Permission
  ): PolicyEvaluationResult {
    const user = this.userManager.getFullUser(userId);
    if (!user) {
      return new PolicyEvaluationResult(AccessDecision.DENY, undefined, '用户不存在');
    }
    if (!user.isActive) {
      return new PolicyEvaluationResult(AccessDecision.DENY, undefined, '用户已停用');
    }

    const resource = this.resourceManager.getResource(resourceId);

    const userPerms = this.getUserEffectivePermissions(userId);
    if (hasPermission(userPerms, Permission.SUPER_ADMIN)) {
      return new PolicyEvaluationResult(AccessDecision.ALLOW, undefined, '超级管理员权限');
    }

    if (resource && resource.ownerId === userId) {
      if (hasPermission(userPerms, permission) || hasPermission(userPerms, Permission.ADMIN)) {
        return new PolicyEvaluationResult(AccessDecision.ALLOW, undefined, '资源所有者');
      }
    }

    const policyResult = this.evaluatePolicies(userId, resourceId, resource?.type, permission);
    if (policyResult.decision !== AccessDecision.ABSTAIN) {
      return policyResult;
    }

    if (hasPermission(userPerms, permission)) {
      return new PolicyEvaluationResult(AccessDecision.ALLOW, undefined, '用户或角色权限匹配');
    }

    return new PolicyEvaluationResult(AccessDecision.DENY, undefined, '无匹配的权限');
  }

  public requireAccess(userId: string, resourceId: string, permission: Permission): void {
    const result = this.checkAccess(userId, resourceId, permission);
    if (!result.isAllowed) {
      throw new PermissionError(`访问被拒绝: ${result.reason || '权限不足'}`);
    }
  }

  public grant(userId: string, permission: Permission): void {
    this.userManager.grantUserPermission(userId, permission);
  }

  public revoke(userId: string, permission: Permission): void {
    this.userManager.revokeUserPermission(userId, permission);
  }

  public assignRole(userId: string, roleId: string): void {
    const role = this.roleManager.getRole(roleId);
    if (!role) {
      throw new AuthError(`角色不存在: ${roleId}`, 'ROLE_NOT_FOUND');
    }
    this.userManager.assignRole(userId, roleId);
  }

  public revokeRole(userId: string, roleId: string): void {
    this.userManager.revokeRole(userId, roleId);
  }

  public createPolicy(params: {
    name: string;
    description?: string;
    effect: AccessDecision;
    principalType: 'USER' | 'ROLE';
    principalIds: string[];
    resourceType?: ResourceType;
    resourceIds?: string[];
    permissions: Permission;
    priority?: number;
    isActive?: boolean;
    conditions?: PolicyCondition[];
  }): AccessPolicy {
    const {
      name,
      description,
      effect,
      principalType,
      principalIds,
      resourceType,
      resourceIds,
      permissions,
      priority = 100,
      isActive = true,
      conditions,
    } = params;

    if (!name || name.trim().length === 0) {
      throw new AuthError('策略名称不能为空', 'INVALID_POLICY_NAME');
    }
    if (!principalIds || principalIds.length === 0) {
      throw new AuthError('策略必须至少指定一个主体', 'EMPTY_PRINCIPALS');
    }
    if (permissions === Permission.NONE) {
      throw new AuthError('策略权限不能为空', 'EMPTY_PERMISSIONS');
    }

    const now = new Date();
    const policy: AccessPolicy = {
      id: uuidv4(),
      name,
      description,
      effect,
      principalType,
      principalIds: [...principalIds],
      resourceType,
      resourceIds: resourceIds ? [...resourceIds] : undefined,
      permissions,
      priority,
      isActive,
      conditions: conditions ? [...conditions] : undefined,
      createdAt: now,
      updatedAt: now,
    };

    this.policies.set(policy.id, policy);
    return policy;
  }

  public getPolicy(policyId: string): AccessPolicy | null {
    return this.policies.get(policyId) ?? null;
  }

  public updatePolicy(policyId: string, updates: Partial<Omit<AccessPolicy, 'id' | 'createdAt'>>): AccessPolicy {
    const policy = this.policies.get(policyId);
    if (!policy) {
      throw new AuthError(`策略不存在: ${policyId}`, 'POLICY_NOT_FOUND');
    }

    Object.assign(policy, updates, { updatedAt: new Date() });
    if (updates.principalIds) policy.principalIds = [...updates.principalIds];
    if (updates.resourceIds) policy.resourceIds = [...updates.resourceIds];
    if (updates.conditions) policy.conditions = [...updates.conditions];
    return policy;
  }

  public deletePolicy(policyId: string): void {
    this.policies.delete(policyId);
  }

  public listPolicies(params?: {
    principalType?: 'USER' | 'ROLE';
    resourceType?: ResourceType;
    isActive?: boolean;
  }): AccessPolicy[] {
    return Array.from(this.policies.values())
      .filter(p => !params?.principalType || p.principalType === params.principalType)
      .filter(p => !params?.resourceType || p.resourceType === params.resourceType)
      .filter(p => params?.isActive === undefined || p.isActive === params.isActive)
      .sort((a, b) => a.priority - b.priority);
  }

  public evaluatePolicies(
    userId: string,
    resourceId: string,
    resourceType: ResourceType | undefined,
    permission: Permission
  ): PolicyEvaluationResult {
    const user = this.userManager.getFullUser(userId);
    if (!user) {
      return new PolicyEvaluationResult(AccessDecision.DENY, undefined, '用户不存在');
    }

    const applicable = this.listPolicies({ isActive: true })
      .filter(p => {
        if (p.resourceType && resourceType && p.resourceType !== resourceType) return false;
        if (p.resourceIds && p.resourceIds.length > 0 && !p.resourceIds.includes(resourceId)) return false;
        if (!hasPermission(p.permissions, permission)) return false;
        return true;
      });

    let allowResult: PolicyEvaluationResult | null = null;
    let denyResult: PolicyEvaluationResult | null = null;

    for (const policy of applicable) {
      const matchesPrincipal = this.policyMatchesPrincipal(policy, userId, user.roles);
      if (!matchesPrincipal) continue;

      const passesConditions = this.checkConditions(policy, userId, resourceId);
      if (!passesConditions) continue;

      const result = new PolicyEvaluationResult(
        policy.effect,
        policy.id,
        `策略 ${policy.name} 匹配`
      );

      if (policy.effect === AccessDecision.DENY && !denyResult) {
        denyResult = result;
      }
      if (policy.effect === AccessDecision.ALLOW && !allowResult) {
        allowResult = result;
      }
    }

    if (denyResult) return denyResult;
    if (allowResult) return allowResult;
    return new PolicyEvaluationResult(AccessDecision.ABSTAIN);
  }

  private policyMatchesPrincipal(policy: AccessPolicy, userId: string, userRoles: string[]): boolean {
    if (policy.principalType === 'USER') {
      return policy.principalIds.includes(userId);
    } else {
      return policy.principalIds.some(rid => userRoles.includes(rid));
    }
  }

  private checkConditions(policy: AccessPolicy, userId: string, resourceId: string): boolean {
    if (!policy.conditions || policy.conditions.length === 0) {
      return true;
    }

    const resource = this.resourceManager.getResource(resourceId);
    const user = this.userManager.getFullUser(userId);

    for (const condition of policy.conditions) {
      if (!this.evaluateCondition(condition, user, resource)) {
        return false;
      }
    }
    return true;
  }

  private evaluateCondition(
    condition: PolicyCondition,
    user: ReturnType<UserManager['getFullUser']>,
    resource: Resource | null
  ): boolean {
    if (condition.type === 'TIME') {
      const now = Date.now();
      return this.compareValues(now, condition.operator, condition.value);
    }

    if (condition.type === 'CUSTOM') {
      return condition.operator === 'EQ' ? !!condition.value : true;
    }

    let actualValue: unknown;
    if (condition.type === 'ATTRIBUTE' && condition.field) {
      if (condition.field.startsWith('resource.') && resource) {
        const key = condition.field.slice('resource.'.length);
        actualValue = (resource.attributes || {})[key];
      } else if (condition.field.startsWith('user.') && user) {
        const key = condition.field.slice('user.'.length);
        actualValue = (user.metadata || {})[key];
      }
    }

    return this.compareValues(actualValue, condition.operator, condition.value);
  }

  private compareValues(actual: unknown, operator: string, expected: unknown): boolean {
    switch (operator) {
      case 'EQ': return actual === expected;
      case 'NE': return actual !== expected;
      case 'GT': return typeof actual === 'number' && typeof expected === 'number' && actual > expected;
      case 'LT': return typeof actual === 'number' && typeof expected === 'number' && actual < expected;
      case 'GTE': return typeof actual === 'number' && typeof expected === 'number' && actual >= expected;
      case 'LTE': return typeof actual === 'number' && typeof expected === 'number' && actual <= expected;
      case 'IN': return Array.isArray(expected) && expected.includes(actual as never);
      case 'NOT_IN': return Array.isArray(expected) && !expected.includes(actual as never);
      case 'CONTAINS': {
        if (typeof actual === 'string' && typeof expected === 'string') {
          return actual.includes(expected);
        }
        if (Array.isArray(actual)) {
          return actual.includes(expected as never);
        }
        return false;
      }
      default: return false;
    }
  }
}
