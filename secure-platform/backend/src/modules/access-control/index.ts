export * from './types';
export { UserManager } from './user-manager';
export { RoleManager, ResourceManager, AccessController } from './rbac';

import { UserManager } from './user-manager';
import { RoleManager, ResourceManager, AccessController } from './rbac';
import { Permission, AuthProvider } from './types';

export interface AccessControlModule {
  userManager: UserManager;
  roleManager: RoleManager;
  resourceManager: ResourceManager;
  accessController: AccessController;
}

export const createAccessControlModule = (): AccessControlModule => {
  const userManager = new UserManager();
  const roleManager = new RoleManager();
  const resourceManager = new ResourceManager();
  const accessController = new AccessController(userManager, roleManager, resourceManager);

  return {
    userManager,
    roleManager,
    resourceManager,
    accessController,
  };
};

export const initDefaultRoles = (roleManager: RoleManager): void => {
  roleManager.createRole({
    name: 'admin',
    description: '系统管理员',
    permissions: Permission.ADMIN | Permission.READ | Permission.WRITE | Permission.DELETE | Permission.CREATE | Permission.UPDATE | Permission.EXECUTE,
    isSystem: true,
  });

  roleManager.createRole({
    name: 'super_admin',
    description: '超级管理员',
    permissions: Permission.SUPER_ADMIN | Permission.ALL,
    isSystem: true,
  });

  roleManager.createRole({
    name: 'user',
    description: '普通用户',
    permissions: Permission.READ,
    isSystem: true,
  });

  roleManager.createRole({
    name: 'auditor',
    description: '审计员',
    permissions: Permission.READ | Permission.EXECUTE,
    isSystem: true,
  });
};

export const initDefaultAdminUser = (userManager: UserManager, roleManager: RoleManager): void => {
  const superAdminRole = roleManager.getRoleByName('super_admin');
  const adminRole = roleManager.getRoleByName('admin');

  userManager.createUser({
    username: 'superadmin',
    email: 'superadmin@secure-platform.local',
    password: 'Super@dmin123!',
    displayName: '超级管理员',
    roles: superAdminRole ? [superAdminRole.id] : [],
    permissions: Permission.SUPER_ADMIN,
    provider: AuthProvider.LOCAL,
  });

  userManager.createUser({
    username: 'admin',
    email: 'admin@secure-platform.local',
    password: 'Admin@123!',
    displayName: '系统管理员',
    roles: adminRole ? [adminRole.id] : [],
    permissions: Permission.ADMIN,
    provider: AuthProvider.LOCAL,
  });
};
