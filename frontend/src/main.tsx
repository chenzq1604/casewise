/**
 * 应用入口文件
 * 挂载React应用到DOM根节点
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/global.css';

/** 获取DOM根节点并挂载React应用 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
