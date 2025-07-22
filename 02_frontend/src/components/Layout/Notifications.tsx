
import React from 'react';
import { X } from 'lucide-react';

interface NotificationItem {
  id: number;
  date: string;
  message: string;
}

interface NotificationsProps {
  isOpen: boolean;
  onClose: () => void;
}

const mockNotifications: NotificationItem[] = [
  {
    id: 1,
    date: '2 June 2025',
    message: 'Market timing restriction has lifted at 11:35 am EST'
  }
];

export const Notifications = ({ isOpen, onClose }: NotificationsProps) => {
  console.log('Notifications component - isOpen:', isOpen);
  
  if (!isOpen) {
    console.log('Notifications not rendering - isOpen is false');
    return null;
  }

  console.log('Notifications component rendering');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-start pt-20">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto border-0">
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center rounded-t-2xl">
          <h2 className="text-2xl font-semibold text-gray-900">Notifications</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <div className="p-6 space-y-4">
          {mockNotifications.map((notification) => (
            <div key={notification.id} className="flex items-start gap-4">
              <div className="text-sm text-gray-500 font-medium flex-shrink-0 w-24">
                {notification.date}
              </div>
              <div className="text-gray-900 text-sm flex-1 leading-relaxed">
                {notification.message}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
