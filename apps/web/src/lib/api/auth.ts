/** Auth payload shapes from /api/v1/auth/*. */

export interface MeUser {
  id: string;
  email: string;
  name: string | null;
  phone?: string | null;
  timezone?: string | null;
  locale?: string | null;
  is_staff?: boolean;
  is_superuser?: boolean;
  is_active?: boolean;
  last_login_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface MeOrganization {
  id: string;
  name: string;
  slug: string;
  status: string;
  plan: string;
  default_timezone?: string;
  default_language?: string;
}

export interface MeMembership {
  organization_id: string;
  organization_name: string;
  role: string;
  status: string;
}

export interface MeResponse {
  user: MeUser;
  organization: MeOrganization | null;
  membership: { role: string; status: string } | null;
  memberships: MeMembership[];
  permissions: string[];
  flags: { can_manage_settings: boolean; can_view_audit: boolean };
}

export interface LoginResponse {
  access: string;
  refresh: string;
  token_type: string;
}
