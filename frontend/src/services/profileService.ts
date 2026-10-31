import { StudentProfile, RevisionItem, LearningRecommendation } from '../types';
import {
  mockStudentProfile,
  mockRevisionItems,
  mockRecommendations,
} from '../mock/mockData';
import { api, apiConfig, simulateDelay } from './apiClient';

export interface TodayPlan {
  suggestedConcepts: LearningRecommendation[];
  dailyPracticeTarget: number;
  completedTodayCount: number;
  upcomingRevisions: RevisionItem[];
}

export class ProfileService {
  private profile: StudentProfile = { ...mockStudentProfile };
  private revisions: RevisionItem[] = [...mockRevisionItems];

  async getStudentProfile(): Promise<StudentProfile> {
    if (!apiConfig.useMock) {
      try {
        const me = await api.get<any>('/auth/me');
        if (me && me.email) {
          return {
            ...this.profile,
            id: me.id,
            email: me.email,
            fullName: me.full_name || 'Emmy Noether (Student)',
            role: (me.role || 'student').toLowerCase() as any,
          };
        }
      } catch (err) {
        console.warn('ProfileService.getStudentProfile live call failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    return { ...this.profile };
  }

  async updatePreferences(
    prefs: Partial<StudentProfile['preferences']>
  ): Promise<StudentProfile> {
    await simulateDelay(150);
    this.profile.preferences = {
      ...this.profile.preferences,
      ...prefs,
    };
    return { ...this.profile };
  }

  async getRevisionQueue(): Promise<RevisionItem[]> {
    await simulateDelay();
    return [...this.revisions];
  }

  async markRevisionReviewed(
    revisionId: string,
    performanceRating: 'hard' | 'good' | 'easy'
  ): Promise<RevisionItem> {
    await simulateDelay(200);
    const item = this.revisions.find((r) => r.id === revisionId);
    if (!item) {
      throw new Error(`Revision item ${revisionId} not found`);
    }

    let newInterval = item.intervalDays;
    let newRetention = item.retentionEstimate;

    if (performanceRating === 'easy') {
      newInterval = item.intervalDays * 2 + 1;
      newRetention = Math.min(100, item.retentionEstimate + 30);
      item.dueStatus = 'scheduled';
    } else if (performanceRating === 'good') {
      newInterval = Math.max(1, Math.round(item.intervalDays * 1.5));
      newRetention = Math.min(100, item.retentionEstimate + 15);
      item.dueStatus = 'scheduled';
    } else {
      newInterval = 1;
      newRetention = Math.max(20, item.retentionEstimate - 20);
      item.dueStatus = 'due_today';
    }

    item.intervalDays = newInterval;
    item.retentionEstimate = newRetention;
    item.lastPracticed = new Date().toISOString();

    return { ...item };
  }

  async getTodayPlan(): Promise<TodayPlan> {
    await simulateDelay();
    return {
      suggestedConcepts: mockRecommendations.slice(0, 2),
      dailyPracticeTarget: 15,
      completedTodayCount: 9,
      upcomingRevisions: this.revisions.filter((r) => r.dueStatus === 'due_today'),
    };
  }
}

export const profileService = new ProfileService();
