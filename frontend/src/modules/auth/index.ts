/**
 * Auth 模块 - 认证与授权
 */

// Components
export { ProtectedRoute } from './components/ProtectedRoute';
export { LoginForm } from './components/LoginForm';
export { RegisterForm } from './components/RegisterForm';
export { ForgotPasswordModal } from './components/ForgotPasswordModal';

// Hooks
export { useAuth } from './hooks/useAuth';

// Services
export { default as authService } from './services/authService';

// Store
export {
  default as authReducer,
  selectIsAuthenticated,
  selectCurrentUser,
  selectAuthLoadingState,
  fetchCurrentUser,
  logout,
} from './store/authSlice';
