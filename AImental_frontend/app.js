// app.js (全局WebSocket与导航栏计算最终合并版)



App({

    // --- 1. 小程序启动生命周期函数 ---
  
    onLaunch() {
  
      // a. 执行你原有的全局导航栏高度计算
  
      this.calculateNavBarDimensions();
  
  
  
      // b. 【新增】启动全局WebSocket管理器
  
      this.webSocketManager.connect();
  
    },
  
  
  
    // --- 2. 全局数据存储 ---
  
    globalData: {
  
      statusBarHeight: 0,
  
      navBarHeight: 0,
  
      totalNavBarHeight: 0
  
      // 你也可以在这里添加其他全局数据，如 userInfo
  
    },
  
  
  
    // --- 3. 全局函数 ---
  
    calculateNavBarDimensions() {
  
      try {
  
        const windowInfo = wx.getWindowInfo();
  
        const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
  
        const extraPadding = 40; // 自定义导航栏与胶囊按钮的间距
  
    
  
        const statusBarHeight = windowInfo.statusBarHeight;
  
        // 计算【标准版】导航栏高度，给其他页面用
  
        const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + extraPadding;
  
        const totalNavBarHeight = statusBarHeight + navBarHeight;
  
    
  
        // --- 【新增代码从这里开始】 ---
  
        // 计算一个【紧凑版】的导航栏高度，专门给聊天列表页面用
  
        // 我们把 extraPadding 减掉，或者只留一个很小的值，比如 10
  
        const compactNavBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + 10; 
  
        const compactTotalNavBarHeight = statusBarHeight + compactNavBarHeight;
  
        // --- 【新增代码到这里结束】 ---
  
    
  
    
  
        // 将【所有】计算结果存入 globalData
  
        this.globalData.statusBarHeight = statusBarHeight;
  
        // 标准版
  
        this.globalData.navBarHeight = navBarHeight;
  
        this.globalData.totalNavBarHeight = totalNavBarHeight;
  
        // 【新增】紧凑版
  
        this.globalData.compactNavBarHeight = compactNavBarHeight;
  
        this.globalData.compactTotalNavBarHeight = compactTotalNavBarHeight;
  
    
  
    
  
      } catch (e) {
  
        // ... catch 部分不用修改 ...
  
        // 为了安全，也给紧凑版加一个备用值
  
        this.globalData.compactNavBarHeight = 44;
  
        this.globalData.compactTotalNavBarHeight = 64;
  
      }
  
    },
  
    
  
    // --- 4. 【核心新增】全局WebSocket管理器 ---
  
    webSocketManager: {
  
      socketTask: null,
  
      isSocketOpen: false,
  
      heartbeatTimer: null,
  
      reconnectTimer: null,
  
      isReconnecting: false,
  
      
  
      // 用于消息回调的当前页面监听器
  
      currentPageListener: null, 
  
  
  
      // 连接函数
  
      connect() {
  
        if (this.isSocketOpen) return;
  
        const token = wx.getStorageSync('token');
  
        if (!token) {
  
          console.log('GlobalWebSocket: 未找到Token，连接已跳过。');
  
          return;
  
        }
  
  
  
        this.socketTask = wx.connectSocket({
  
          url: 'wss://api.feelyourself.cn/api/v1/community/ws?token=' + token,
  
        });
  
  
  
        this.bindSocketEvents();
  
      },
  
  
  
      // 绑定事件
  
      bindSocketEvents() {
  
        this.socketTask.onOpen(() => {
  
          console.log('GlobalWebSocket: 连接已打开。');
  
          this.isSocketOpen = true;
  
          this.isReconnecting = false;
  
          this.clearReconnectTimer();
  
          this.startHeartbeat();
  
        });
  
  
  
        this.socketTask.onMessage((res) => {
  
          // 当收到消息时，检查是否有页面正在“监听”
  
          if (this.currentPageListener && typeof this.currentPageListener.onSocketMessage === 'function') {
  
            try {
  
              const data = JSON.parse(res.data);
  
              // 调用监听页面的回调函数，把消息传过去
  
              this.currentPageListener.onSocketMessage(data);
  
            } catch (e) {
  
              console.error('GlobalWebSocket: 解析消息失败:', e);
  
            }
  
          }
  
        });
  
  
  
        this.socketTask.onClose(() => {
  
          console.log('GlobalWebSocket: 连接已关闭。');
  
          this.isSocketOpen = false;
  
          this.stopHeartbeat();
  
          this.reconnect();
  
        });
  
  
  
        this.socketTask.onError((err) => {
  
          console.error('GlobalWebSocket: 发生错误:', err);
  
          this.isSocketOpen = false;
  
          // 发生错误时也尝试重连
  
          this.reconnect();
  
        });
  
      },
  
  
  
      // 注册和注销监听页面的函数
  
      registerListener(pageInstance) {
  
        console.log('GlobalWebSocket: 页面注册为监听器。');
  
        this.currentPageListener = pageInstance;
  
      },
  
      unregisterListener() {
  
        console.log('GlobalWebSocket: 页面注销监听器。');
  
        this.currentPageListener = null;
  
      },
  
  
  
      // 全局发送消息函数 (如果需要从全局发送的话)
  
      sendMessage(data) {
  
        if (this.isSocketOpen) {
  
          this.socketTask.send({ data: JSON.stringify(data) });
  
        } else {
  
          console.error('GlobalWebSocket: Socket未连接，消息发送失败:', data);
  
          wx.showToast({ title: '网络连接已断开', icon: 'none' });
  
        }
  
      },
  
  
  
      // 心跳和重连机制
  
      startHeartbeat() {
  
        this.stopHeartbeat();
  
        this.heartbeatTimer = setInterval(() => {
  
          this.sendMessage({ type: 'heartbeat' });
  
        }, 30000);
  
      },
  
      stopHeartbeat() {
  
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  
      },
  
      reconnect() {
  
        if (this.isReconnecting) return;
  
        this.isReconnecting = true;
  
        this.clearReconnectTimer();
  
        this.reconnectTimer = setTimeout(() => {
  
          console.log('GlobalWebSocket: 正在重连...');
  
          this.connect();
  
        }, 5000); // 5秒后重连
  
      },
  
      clearReconnectTimer() {
  
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
  
      }
  
    }
  
  })