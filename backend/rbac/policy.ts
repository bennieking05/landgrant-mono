export type Persona = 'landowner' | 'land_agent' | 'in_house_counsel' | 'outside_counsel' | 'admin';
export type Action = 'read' | 'write' | 'approve' | 'execute';

export const POLICY: Record<Persona, Record<string, Action[]>> = {
  landowner: {
    portal: ['read', 'write'],
    decision: ['execute'],
  },
  land_agent: {
    parcel: ['read', 'write'],
    communication: ['read', 'write'],
    packet: ['execute'],
  },
  in_house_counsel: {
    template: ['read', 'write', 'approve'],
    binder: ['read', 'approve'],
    budget: ['read', 'write'],
  },
  outside_counsel: {
    case: ['read', 'write'],
    deadline: ['read', 'write'],
    status: ['execute'],
  },
  admin: {
    rbac: ['read', 'write'],
    audit: ['read'],
  },
};
