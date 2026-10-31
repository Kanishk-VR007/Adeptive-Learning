import { describe, it, expect, beforeEach } from 'vitest';
import { learningService } from '../services/learningService';
import { progressService } from '../services/progressService';
import { profileService } from '../services/profileService';

describe('Frontend API Abstraction & Services Layer', () => {
  describe('learningService', () => {
    it('loads subjects with correct typed attributes', async () => {
      const subjects = await learningService.getSubjects();
      expect(subjects).toBeDefined();
      expect(subjects.length).toBeGreaterThan(0);
      expect(subjects[0]).toHaveProperty('code');
      expect(subjects[0]).toHaveProperty('name');
      expect(subjects[0]).toHaveProperty('totalConcepts');
    });

    it('loads concepts filtered by subjectId', async () => {
      const concepts = await learningService.getConcepts(1);
      expect(concepts.length).toBeGreaterThan(0);
      concepts.forEach((c) => {
        expect(c.subjectId).toBe(1);
        expect(c).toHaveProperty('conceptCode');
        expect(c).toHaveProperty('learningObjectives');
      });
    });

    it('retrieves questions for concept', async () => {
      const questions = await learningService.getQuestionsForConcept(6);
      expect(questions.length).toBeGreaterThan(0);
      expect(questions[0].conceptId).toBe(6);
      expect(questions[0].options?.length).toBeGreaterThanOrEqual(2);
      expect(questions[0].hints.length).toBeGreaterThan(0);
    });

    it('evaluates CORRECT answer deterministically and increases BKT mastery', async () => {
      const result = await learningService.submitAnswer({
        questionId: 101,
        selectedOptionId: 'B', // Correct option for Q101
        timeSpentSeconds: 12,
        hintsRequested: 0,
      });

      expect(result.outcome).toBe('correct');
      expect(result.isCorrect).toBe(true);
      expect(result.score).toBe(1.0);
      expect(result.masteryDelta).toBeGreaterThan(0);
      expect(result.updatedMastery).toBeGreaterThan(result.previousMastery);
      expect(result.recommendedAction.type).toMatch(/next_question|concept_mastered/);
    });

    it('evaluates PARTIALLY CORRECT answer with constructive pedagogical guidance', async () => {
      const result = await learningService.submitAnswer({
        questionId: 101,
        selectedOptionId: 'A', // Partial credit option: outer differentiated, forgot inner
        timeSpentSeconds: 15,
        hintsRequested: 1,
      });

      expect(result.outcome).toBe('partially_correct');
      expect(result.isCorrect).toBe(false);
      expect(result.score).toBe(0.5);
      expect(result.socraticHint).toBeDefined();
      expect(result.conceptClarification).toContain('inner');
    });

    it('evaluates INCORRECT answer with Socratic hint and reduces BKT mastery', async () => {
      const result = await learningService.submitAnswer({
        questionId: 101,
        selectedOptionId: 'D', // Wrong option
        timeSpentSeconds: 20,
        hintsRequested: 0,
      });

      expect(result.outcome).toBe('incorrect');
      expect(result.isCorrect).toBe(false);
      expect(result.score).toBe(0.0);
      expect(result.masteryDelta).toBeLessThan(0);
      expect(result.socraticHint).toBeDefined();
    });

    it('requests progressive hints stepwise', async () => {
      const hint1 = await learningService.requestHint(101, 0);
      expect(hint1.hint).toBeDefined();
      expect(hint1.hasMore).toBe(true);

      const hintFinal = await learningService.requestHint(101, 2);
      expect(hintFinal.hint).toBeDefined();
      expect(hintFinal.hasMore).toBe(false);
    });

    it('handles non-existent question gracefully with thrown error', async () => {
      await expect(
        learningService.submitAnswer({
          questionId: 99999,
          selectedOptionId: 'A',
          timeSpentSeconds: 5,
          hintsRequested: 0,
        })
      ).rejects.toThrow('not found');
    });
  });

  describe('progressService', () => {
    it('returns overall mastery overview with calculated metrics', async () => {
      const overview = await progressService.getOverallOverview();
      expect(overview.overallMasteryPercentage).toBeGreaterThanOrEqual(0);
      expect(overview.overallMasteryPercentage).toBeLessThanOrEqual(100);
      expect(overview.totalConceptsLearned).toBeGreaterThan(0);
      expect(overview.studyStreakDays).toBe(7);
    });

    it('returns weak concepts sorted ascending by mastery', async () => {
      const weak = await progressService.getWeakConcepts(3);
      expect(weak.length).toBeLessThanOrEqual(3);
      for (let i = 0; i < weak.length - 1; i++) {
        expect(weak[i].currentMastery).toBeLessThanOrEqual(weak[i + 1].currentMastery);
      }
    });

    it('returns strong concepts sorted descending by mastery', async () => {
      const strong = await progressService.getStrongConcepts(3);
      expect(strong.length).toBeLessThanOrEqual(3);
      for (let i = 0; i < strong.length - 1; i++) {
        expect(strong[i].currentMastery).toBeGreaterThanOrEqual(strong[i + 1].currentMastery);
      }
    });

    it('provides valid 2D DAG graph with nodes and directed edges', async () => {
      const graph = await progressService.getConceptGraph(1);
      expect(graph.nodes.length).toBeGreaterThan(0);
      expect(graph.edges.length).toBeGreaterThan(0);
      graph.edges.forEach((edge) => {
        expect(edge).toHaveProperty('fromConceptId');
        expect(edge).toHaveProperty('toConceptId');
      });
    });
  });

  describe('profileService', () => {
    it('fetches student profile correctly', async () => {
      const profile = await profileService.getStudentProfile();
      expect(profile.fullName).toBe('Alex Chen');
      expect(profile.studyStreakDays).toBe(7);
      expect(profile.preferences).toBeDefined();
    });

    it('updates user preferences idempotently', async () => {
      const updated = await profileService.updatePreferences({ reducedMotion: true });
      expect(updated.preferences.reducedMotion).toBe(true);

      const restored = await profileService.updatePreferences({ reducedMotion: false });
      expect(restored.preferences.reducedMotion).toBe(false);
    });

    it('updates spaced repetition review item schedule', async () => {
      const reviewed = await profileService.markRevisionReviewed('rev-1', 'easy');
      expect(reviewed.dueStatus).toBe('scheduled');
      expect(reviewed.retentionEstimate).toBeGreaterThanOrEqual(70);
    });
  });
});
