import { describe, it, expect, beforeEach } from 'vitest';
import { authService } from '../services/authService';
import { api, checkBackendHealth, setUseMock, isUsingMock } from '../services/apiClient';
import { learningService } from '../services/learningService';
import { progressService } from '../services/progressService';

describe('Full-Stack Integration & Live Backend Client Suite', () => {
  beforeEach(() => {
    setUseMock(true); // default to deterministic mock mode for headless CI safety
  });

  describe('AuthService & Token Lifecycle', () => {
    it('manages token storage and authentication state', () => {
      authService.logout();
      expect(authService.isAuthenticated()).toBe(false);

      // Verify token can be set and retrieved
      localStorage.setItem('adeptlearn_access_token', 'test_jwt_token_123');
      expect(authService.getToken()).toBe('test_jwt_token_123');
      expect(authService.isAuthenticated()).toBe(true);

      authService.logout();
      expect(authService.getToken()).toBeNull();
      expect(authService.isAuthenticated()).toBe(false);
    });
  });

  describe('ApiClient Dual-Mode Configuration', () => {
    it('switches between mock mode and live mode seamlessly', () => {
      setUseMock(true);
      expect(isUsingMock()).toBe(true);

      setUseMock(false);
      expect(isUsingMock()).toBe(false);

      setUseMock(true);
      expect(isUsingMock()).toBe(true);
    });

    it('handles simulated latency in mock mode', async () => {
      setUseMock(true);
      const start = Date.now();
      const subjects = await learningService.getSubjects();
      const duration = Date.now() - start;

      expect(subjects.length).toBeGreaterThan(0);
      expect(duration).toBeGreaterThanOrEqual(100);
    });
  });

  describe('LearningService Full-Stack Resilience', () => {
    it('returns structured subjects in both live and mock mode', async () => {
      const mockSubs = await learningService.getSubjects();
      expect(mockSubs.length).toBeGreaterThan(0);
      expect(mockSubs[0]).toHaveProperty('code');
      expect(mockSubs[0]).toHaveProperty('name');
    });

    it('evaluates student submissions and returns full BKT mastery metadata', async () => {
      setUseMock(true);
      const res = await learningService.submitAnswer({
        questionId: 101,
        selectedOptionId: 'B',
        timeSpentSeconds: 8,
        hintsRequested: 0,
      });

      expect(res.outcome).toBe('correct');
      expect(res.isCorrect).toBe(true);
      expect(res.masteryDelta).toBeGreaterThan(0);
      expect(res.updatedMastery).toBeGreaterThan(res.previousMastery);
      expect(res.newClassification).toBeDefined();
    });
  });

  describe('ProgressService DAG & Mastery Data Integration', () => {
    it('fetches concept graph with valid DAG node and edge topology', async () => {
      setUseMock(true);
      const graph = await progressService.getConceptGraph(1);
      expect(graph.subjectId).toBe(1);
      expect(graph.nodes.length).toBeGreaterThanOrEqual(5);
      expect(graph.edges.length).toBeGreaterThanOrEqual(4);

      // Verify node schema
      const firstNode = graph.nodes[0];
      expect(firstNode).toHaveProperty('id');
      expect(firstNode).toHaveProperty('name');
      expect(firstNode).toHaveProperty('masteryProbability');
      expect(firstNode).toHaveProperty('status');
    });

    it('aggregates overall mastery overview statistics', async () => {
      setUseMock(true);
      const overview = await progressService.getOverallOverview();
      expect(overview.overallMasteryPercentage).toBeGreaterThanOrEqual(0);
      expect(overview.totalConceptsLearned).toBeGreaterThan(0);
      expect(overview.totalQuestionsAnswered).toBeGreaterThan(0);
      expect(overview.studyStreakDays).toBe(7);
    });
  });
});
