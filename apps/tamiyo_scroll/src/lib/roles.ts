import type { UserRole } from '@barrins/goblin-guide'

/**
 * Ordinal level of the identity token's `role` claim, mirroring
 * `apps/barrins_identity/app/models/user.py`'s `UserRole.level` hierarchy:
 * `user < moderator < ml_developer < admin`.
 *
 * `AppShell.tsx`/`useAdmin.ts`'s existing precedent (`role === 'admin'`) is
 * an *exact* match, which only works because `admin` happens to be the top
 * of the hierarchy. A floor check (e.g. "moderator or above") needs an
 * ordinal comparison instead — `moderator`, `ml_developer` and `admin` all
 * satisfy a `moderator` floor.
 */
const ROLE_LEVEL: Record<UserRole, number> = {
  user: 1,
  moderator: 2,
  ml_developer: 3,
  admin: 4,
}

/**
 * Whether `role` meets or exceeds `floor` in the role hierarchy above.
 *
 * This is a UX convenience only (Constitution §4.1) — e.g. gating the
 * #123/#124 mulligan/misplay stepper+comment controls to a `moderator`+
 * `currentUser` so a sub-moderator account never sees fields it can't
 * actually submit. The real enforcement boundary is always backend-side
 * (a field-level `403` for these fields, in `_apply_payload`); this check
 * exists purely to avoid rendering a control that would fail server-side,
 * never to grant or withhold access on its own.
 */
export function roleMeetsFloor(role: UserRole | undefined, floor: UserRole): boolean {
  if (!role) return false
  return ROLE_LEVEL[role] >= ROLE_LEVEL[floor]
}
