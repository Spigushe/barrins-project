export { IdentityProvider } from './auth/IdentityProvider'
export type { IdentityConfig, IdentityProviderProps } from './auth/IdentityProvider'
export {
  useIdentity,
  useCurrentUser,
  useLogin,
  useLogout,
  useSignup,
  useVerifyEmail,
  useResendVerification,
} from './auth/hooks'
export type { LoginVariables, VerifyEmailVariables } from './auth/hooks'
export { createIdentityClient, IdentityError } from './auth/client'
export type { IdentityClient, IdentityClientOptions, SignupInput } from './auth/client'
export { createMemoryTokenStore } from './auth/tokenStore'
export type { TokenStore } from './auth/tokenStore'
export type {
  Principal,
  TokenPair,
  UserRole,
  SignupResponse,
  ResendVerificationResponse,
} from './auth/schemas'
export { LoginScreen } from './components/LoginScreen'
export type { LoginScreenProps } from './components/LoginScreen'
export { SignupScreen } from './components/SignupScreen'
export type { SignupScreenProps } from './components/SignupScreen'
export { VerifyEmailScreen } from './components/VerifyEmailScreen'
export type { VerifyEmailScreenProps } from './components/VerifyEmailScreen'
