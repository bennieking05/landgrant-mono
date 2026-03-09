/**
 * Task Management UI Component
 * 
 * Provides comprehensive task management including:
 * - Task list with filtering and sorting
 * - Task creation with auto-assignment
 * - Workload-based assignment suggestions
 * - Priority and status management
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types
interface Task {
  id: string;
  project_id: string;
  parcel_id?: string;
  title: string;
  description?: string;
  category: string;
  priority: string;
  status: string;
  persona: string;
  assigned_to?: string;
  assigned_to_name?: string;
  due_at?: string;
  created_at: string;
  is_overdue: boolean;
  metadata: Record<string, unknown>;
}

interface TaskStats {
  total: number;
  open: number;
  in_progress: number;
  completed: number;
  overdue: number;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  by_assignee: Array<{ user_id: string; user_name: string; count: number }>;
}

interface AssignmentSuggestion {
  user_id: string;
  user_name: string;
  persona: string;
  current_workload: number;
  reason: string;
  score: number;
}

interface TaskManagerProps {
  projectId?: string;
  parcelId?: string;
  userId?: string;
}

// Constants
const TASK_CATEGORIES = [
  { value: 'document_review', label: 'Document Review', icon: '📄' },
  { value: 'approval_required', label: 'Approval Required', icon: '✅' },
  { value: 'owner_contact', label: 'Owner Contact', icon: '📞' },
  { value: 'deadline_action', label: 'Deadline Action', icon: '⏰' },
  { value: 'offer_preparation', label: 'Offer Preparation', icon: '📝' },
  { value: 'appraisal_review', label: 'Appraisal Review', icon: '🏠' },
  { value: 'litigation_prep', label: 'Litigation Prep', icon: '⚖️' },
  { value: 'general', label: 'General', icon: '📋' },
];

const TASK_PRIORITIES = [
  { value: 'critical', label: 'Critical', color: 'bg-red-100 text-red-800 border-red-200' },
  { value: 'high', label: 'High', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  { value: 'low', label: 'Low', color: 'bg-gray-100 text-gray-800 border-gray-200' },
];

const TASK_STATUSES = [
  { value: 'open', label: 'Open', color: 'bg-blue-100 text-blue-800' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-purple-100 text-purple-800' },
  { value: 'blocked', label: 'Blocked', color: 'bg-red-100 text-red-800' },
  { value: 'completed', label: 'Completed', color: 'bg-green-100 text-green-800' },
  { value: 'cancelled', label: 'Cancelled', color: 'bg-gray-100 text-gray-500' },
];

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8050';

export const TaskManager: React.FC<TaskManagerProps> = ({
  projectId,
  parcelId,
  userId,
}) => {
  // State
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);
  
  // UI State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [suggestions, setSuggestions] = useState<AssignmentSuggestion[]>([]);
  
  // Create Task Form
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    category: 'general',
    priority: '',
    due_at: '',
    auto_assign: true,
  });

  // Load tasks
  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      if (parcelId) params.append('parcel_id', parcelId);
      if (statusFilter) params.append('status', statusFilter);
      if (priorityFilter) params.append('priority', priorityFilter);
      if (categoryFilter) params.append('category', categoryFilter);
      if (showOverdueOnly) params.append('overdue_only', 'true');
      
      const response = await fetch(`${API_BASE}/tasks?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to load tasks');
      
      const data = await response.json();
      setTasks(data.tasks);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, [projectId, parcelId, statusFilter, priorityFilter, categoryFilter, showOverdueOnly]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      
      const response = await fetch(`${API_BASE}/tasks/stats/summary?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to load stats');
      
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, [projectId]);

  useEffect(() => {
    loadTasks();
    loadStats();
  }, [loadTasks, loadStats]);

  // Create task
  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId || 'PRJ-001',
          parcel_id: parcelId,
          ...newTask,
          due_at: newTask.due_at ? new Date(newTask.due_at).toISOString() : null,
        }),
      });
      
      if (!response.ok) throw new Error('Failed to create task');
      
      setShowCreateModal(false);
      setNewTask({
        title: '',
        description: '',
        category: 'general',
        priority: '',
        due_at: '',
        auto_assign: true,
      });
      loadTasks();
      loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  // Update task status
  const handleStatusChange = async (taskId: string, newStatus: string) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (!response.ok) throw new Error('Failed to update task');
      
      loadTasks();
      loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task');
    }
  };

  // Complete task
  const handleCompleteTask = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) throw new Error('Failed to complete task');
      
      loadTasks();
      loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete task');
    }
  };

  // Get assignment suggestions
  const handleShowAssign = async (task: Task) => {
    setSelectedTask(task);
    try {
      const response = await fetch(`${API_BASE}/tasks/${task.id}/suggest-assignee`);
      if (!response.ok) throw new Error('Failed to get suggestions');
      
      const data = await response.json();
      setSuggestions(data);
      setShowAssignModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get suggestions');
    }
  };

  // Assign task
  const handleAssignTask = async (taskId: string, userId: string) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/assign?user_id=${userId}`, {
        method: 'POST',
      });
      
      if (!response.ok) throw new Error('Failed to assign task');
      
      setShowAssignModal(false);
      loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign task');
    }
  };

  // Auto-assign task
  const handleAutoAssign = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/auto-assign`, {
        method: 'POST',
      });
      
      if (!response.ok) throw new Error('Failed to auto-assign task');
      
      setShowAssignModal(false);
      loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to auto-assign task');
    }
  };

  // Get priority style
  const getPriorityStyle = (priority: string) => {
    const p = TASK_PRIORITIES.find(p => p.value === priority);
    return p?.color || 'bg-gray-100 text-gray-800';
  };

  // Get status style
  const getStatusStyle = (status: string) => {
    const s = TASK_STATUSES.find(s => s.value === status);
    return s?.color || 'bg-gray-100 text-gray-800';
  };

  // Get category icon
  const getCategoryIcon = (category: string) => {
    const c = TASK_CATEGORIES.find(c => c.value === category);
    return c?.icon || '📋';
  };

  // Format due date
  const formatDueDate = (dateStr?: string) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = new Date();
    const diff = date.getTime() - now.getTime();
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    
    if (days < 0) return { text: `${Math.abs(days)} days overdue`, class: 'text-red-600' };
    if (days === 0) return { text: 'Due today', class: 'text-orange-600' };
    if (days === 1) return { text: 'Due tomorrow', class: 'text-yellow-600' };
    return { text: `Due in ${days} days`, class: 'text-gray-600' };
  };

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Task Manager</h2>
            <p className="text-sm text-gray-500 mt-1">
              Manage and track tasks with auto-assignment
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Task
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="grid grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
              <div className="text-xs text-gray-500">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.open}</div>
              <div className="text-xs text-gray-500">Open</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{stats.in_progress}</div>
              <div className="text-xs text-gray-500">In Progress</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
              <div className="text-xs text-gray-500">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{stats.overdue}</div>
              <div className="text-xs text-gray-500">Overdue</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex flex-wrap gap-3 items-center">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Statuses</option>
          {TASK_STATUSES.filter(s => s.value !== 'cancelled').map(status => (
            <option key={status.value} value={status.value}>{status.label}</option>
          ))}
        </select>
        
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Priorities</option>
          {TASK_PRIORITIES.map(priority => (
            <option key={priority.value} value={priority.value}>{priority.label}</option>
          ))}
        </select>
        
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Categories</option>
          {TASK_CATEGORIES.map(category => (
            <option key={category.value} value={category.value}>
              {category.icon} {category.label}
            </option>
          ))}
        </select>
        
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showOverdueOnly}
            onChange={(e) => setShowOverdueOnly(e.target.checked)}
            className="rounded"
          />
          <span className="text-red-600">Overdue only</span>
        </label>
        
        <button
          onClick={() => {
            setStatusFilter('');
            setPriorityFilter('');
            setCategoryFilter('');
            setShowOverdueOnly(false);
          }}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Clear filters
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-200">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Task List */}
      <div className="divide-y divide-gray-200">
        {loading ? (
          <div className="px-6 py-12 text-center text-gray-500">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            Loading tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>No tasks found</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 text-blue-600 hover:text-blue-700"
            >
              Create your first task
            </button>
          </div>
        ) : (
          tasks.map(task => {
            const dueInfo = formatDueDate(task.due_at);
            return (
              <div
                key={task.id}
                className={`px-6 py-4 hover:bg-gray-50 ${task.is_overdue ? 'bg-red-50' : ''}`}
              >
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <button
                    onClick={() => task.status !== 'completed' && handleCompleteTask(task.id)}
                    className={`mt-1 w-5 h-5 rounded border-2 flex items-center justify-center ${
                      task.status === 'completed'
                        ? 'bg-green-500 border-green-500 text-white'
                        : 'border-gray-300 hover:border-green-500'
                    }`}
                  >
                    {task.status === 'completed' && (
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                  
                  {/* Task Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getCategoryIcon(task.category)}</span>
                      <h3 className={`font-medium ${task.status === 'completed' ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                        {task.title}
                      </h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getPriorityStyle(task.priority)}`}>
                        {task.priority}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusStyle(task.status)}`}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>
                    
                    {task.description && (
                      <p className="text-sm text-gray-500 mt-1">{task.description}</p>
                    )}
                    
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      {dueInfo && (
                        <span className={dueInfo.class}>
                          {dueInfo.text}
                        </span>
                      )}
                      {task.assigned_to_name && (
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                          </svg>
                          {task.assigned_to_name}
                        </span>
                      )}
                      {task.parcel_id && (
                        <span className="text-gray-400">Parcel: {task.parcel_id}</span>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {task.status !== 'completed' && (
                      <>
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(task.id, e.target.value)}
                          className="text-xs px-2 py-1 border border-gray-300 rounded"
                        >
                          {TASK_STATUSES.filter(s => s.value !== 'cancelled').map(status => (
                            <option key={status.value} value={status.value}>{status.label}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleShowAssign(task)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50"
                          title="Assign task"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                          </svg>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Create New Task</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 hover:bg-gray-100 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleCreateTask} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter task title..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                  placeholder="Enter task description..."
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newTask.category}
                    onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {TASK_CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>
                        {cat.icon} {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={newTask.priority}
                    onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Auto (based on category)</option>
                    {TASK_PRIORITIES.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                <input
                  type="datetime-local"
                  value={newTask.due_at}
                  onChange={(e) => setNewTask({ ...newTask, due_at: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newTask.auto_assign}
                  onChange={(e) => setNewTask({ ...newTask, auto_assign: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">Auto-assign based on workload</span>
              </label>
              
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assignment Modal */}
      {showAssignModal && selectedTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Assign Task</h3>
                <p className="text-sm text-gray-500">{selectedTask.title}</p>
              </div>
              <button
                onClick={() => setShowAssignModal(false)}
                className="p-1 hover:bg-gray-100 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6">
              <div className="mb-4">
                <button
                  onClick={() => handleAutoAssign(selectedTask.id)}
                  className="w-full px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Auto-assign based on workload
                </button>
              </div>
              
              <div className="text-sm text-gray-500 mb-3">Or choose a team member:</div>
              
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {suggestions.map(suggestion => (
                  <button
                    key={suggestion.user_id}
                    onClick={() => handleAssignTask(selectedTask.id, suggestion.user_id)}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-left flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium text-gray-900">{suggestion.user_name}</div>
                      <div className="text-xs text-gray-500">
                        {suggestion.persona} • {suggestion.current_workload} active tasks
                      </div>
                      <div className="text-xs text-gray-400 mt-1">{suggestion.reason}</div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      suggestion.score >= 80 ? 'bg-green-100 text-green-700' :
                      suggestion.score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {Math.round(suggestion.score)}%
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskManager;
