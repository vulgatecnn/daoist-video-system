import React from 'react';
import { Provider } from 'react-redux';
import { store } from './store';
import AppRouter from './components/Router';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <div className="App">
          <AppRouter />
        </div>
      </Provider>
    </ErrorBoundary>
  );
}

export default App;
