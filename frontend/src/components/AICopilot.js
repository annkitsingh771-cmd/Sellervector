import React, { useState } from 'react';
import { X, Sparkles, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const AICopilot = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I\'m your AI Copilot. I can help you optimize your campaigns, detect wasted spend, forecast inventory, and provide actionable insights. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiClient.post('/ai-copilot', { message: input });
      const aiMessage = {
        role: 'assistant',
        content: response.data.response,
        suggestions: response.data.suggestions
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      toast.error('Failed to get AI response');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white border-l border-slate-200 shadow-xl flex flex-col slide-in-right" style={{ zIndex: 9999 }}>
      {/* Header */}
      <div className="bg-indigo-700 text-white p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-sm flex items-center justify-center">
            <Sparkles size={20} />
          </div>
          <div>
            <h2 className="font-bold text-lg" style={{ fontFamily: 'Chivo, sans-serif' }}>AI Copilot</h2>
            <p className="text-indigo-200 text-xs">Your intelligent assistant</p>
          </div>
        </div>
        <Button
          onClick={onClose}
          data-testid="close-copilot-button"
          variant="ghost"
          size="icon"
          className="text-white hover:bg-indigo-600 rounded-sm"
        >
          <X size={20} />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-sm p-3 ${
                msg.role === 'user'
                  ? 'bg-indigo-700 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}
            >
              <p className="text-sm leading-relaxed">{msg.content}</p>
              {msg.suggestions && (
                <div className="mt-3 space-y-2">
                  {msg.suggestions.map((suggestion, i) => (
                    <button
                      key={i}
                      data-testid={`suggestion-${i}`}
                      className="block w-full text-left text-xs bg-white border border-slate-200 rounded-sm px-3 py-2 hover:bg-slate-50 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-sm p-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask anything..."
            data-testid="ai-copilot-input"
            className="flex-1 border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
          />
          <Button
            onClick={sendMessage}
            data-testid="send-message-button"
            disabled={!input.trim() || loading}
            className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm transition-all duration-150 active:scale-95"
          >
            <Send size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AICopilot;
