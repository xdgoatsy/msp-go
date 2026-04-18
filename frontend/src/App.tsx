import { AppProviders } from './app/providers';
import { AppRoutes } from './app/routes/AppRoutes';

/**
 * 应用根组件
 * 职责单一：组合 Provider 层和路由层
 */
function App() {
  return (
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  );
}

export default App;
