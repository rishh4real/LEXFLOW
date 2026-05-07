import React, { useState, useEffect } from 'react';
import { Bell, AlertCircle } from 'lucide-react';
import client from '../api/client';

const NotificationTicker = () => {
  const [alerts, setAlerts] = useState([]);

  const fetchAlerts = async () => {
    try {
      const res = await client.get('/dashboard/alerts');
      setAlerts(res.data);
    } catch (err) {
      console.error('Failed to fetch alerts');
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (alerts.length === 0) return null;

  return (
    <div className="bg-white text-black py-2 overflow-hidden border-y border-black">
      <div className="flex animate-marquee whitespace-nowrap items-center">
        {alerts.map((alert, i) => (
          <div key={i} className="mx-8 flex items-center gap-2">
            <span className="font-black text-[10px] tracking-widest uppercase">
              {alert.status === 'flagged' ? '⚠️ URGENT' : '✨ NEW VERIFIED'}
            </span>
            <span className="text-xs font-medium">
              {alert.message}
            </span>
            <span className="text-[10px] opacity-50">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
        {/* Duplicate for infinite effect */}
        {alerts.map((alert, i) => (
          <div key={`dup-${i}`} className="mx-8 flex items-center gap-2">
            <span className="font-black text-[10px] tracking-widest uppercase">
              {alert.status === 'flagged' ? '⚠️ URGENT' : '✨ NEW VERIFIED'}
            </span>
            <span className="text-xs font-medium">
              {alert.message}
            </span>
            <span className="text-[10px] opacity-50">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NotificationTicker;
