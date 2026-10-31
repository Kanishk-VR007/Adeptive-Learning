import {
  ConceptMastery,
  ConceptGraphData,
  LearningRecommendation,
  ActivitySummary,
} from '../types';
import {
  mockMasteryRecords,
  mockConceptGraph,
  mockRecommendations,
  mockActivityHistory,
  mockSubjects,
} from '../mock/mockData';
import { api, apiConfig, simulateDelay } from './apiClient';

export interface SubjectProgressSummary {
  subjectId: number;
  subjectCode: string;
  subjectName: string;
  totalConcepts: number;
  masteredCount: number;
  inProgressCount: number;
  weakCount: number;
  averageMastery: number; // 0 to 100%
  colorScheme: string;
}

export interface OverallMasteryOverview {
  overallMasteryPercentage: number;
  totalConceptsLearned: number;
  totalConceptsMastered: number;
  totalQuestionsAnswered: number;
  totalStudyMinutes: number;
  studyStreakDays: number;
}

export class ProgressService {
  async getOverallOverview(): Promise<OverallMasteryOverview> {
    if (!apiConfig.useMock) {
      try {
        const masterySum = await api.get<any>('/mastery/me/subject/1');
        if (masterySum && typeof masterySum.total_concepts === 'number') {
          const avgMastery = Math.round((masterySum.average_mastery || 0.30) * 100);
          return {
            overallMasteryPercentage: avgMastery,
            totalConceptsLearned: masterySum.total_concepts,
            totalConceptsMastered: masterySum.mastered_count || 0,
            totalQuestionsAnswered: (masterySum.concepts || []).reduce((acc: number, c: any) => acc + (c.practice_count || 0), 0) || 76,
            totalStudyMinutes: 340,
            studyStreakDays: 7,
          };
        }
      } catch (err) {
        console.warn('ProgressService.getOverallOverview live call failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    const records = mockMasteryRecords;
    const totalMastery = records.reduce((acc, curr) => acc + curr.currentMastery, 0);
    const avgMastery = Math.round((totalMastery / records.length) * 100);
    const masteredCount = records.filter((r) => r.currentMastery >= 0.90).length;
    const totalQuestions = records.reduce((acc, curr) => acc + curr.totalAttempts, 0);

    return {
      overallMasteryPercentage: avgMastery,
      totalConceptsLearned: records.length,
      totalConceptsMastered: masteredCount,
      totalQuestionsAnswered: totalQuestions,
      totalStudyMinutes: 335,
      studyStreakDays: 7,
    };
  }

  async getAllConceptMasteries(subjectId?: number): Promise<ConceptMastery[]> {
    if (!apiConfig.useMock) {
      try {
        const targetId = subjectId || 1;
        const masterySum = await api.get<any>(`/mastery/me/subject/${targetId}`);
        if (masterySum && Array.isArray(masterySum.concepts) && masterySum.concepts.length > 0) {
          return masterySum.concepts.map((c: any) => {
            const prob = c.mastery_probability ?? 0.20;
            const tier =
              prob >= 0.90 ? 'Mastered' :
              prob >= 0.70 ? 'Good Understanding' :
              prob >= 0.40 ? 'Developing Understanding' : 'Weak Understanding';

            return {
              id: c.concept_id,
              studentId: masterySum.user_id || 2,
              conceptId: c.concept_id,
              conceptCode: c.concept_code || `C${c.concept_id}`,
              conceptName: c.concept_name,
              chapterId: c.chapter_id || 1,
              subjectId: targetId,
              initialMastery: 0.20,
              currentMastery: Number(prob.toFixed(2)),
              masteryClassification: tier,
              totalAttempts: c.practice_count || 0,
              correctAttempts: Math.round((c.practice_count || 0) * (prob >= 0.5 ? 0.75 : 0.3)),
              incorrectAttempts: Math.round((c.practice_count || 0) * (prob >= 0.5 ? 0.25 : 0.7)),
              lastAttemptAt: c.last_practiced_at,
              history: [],
            };
          });
        }
      } catch (err) {
        console.warn('ProgressService.getAllConceptMasteries live call failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    if (subjectId) {
      return mockMasteryRecords.filter((m) => m.subjectId === subjectId);
    }
    return [...mockMasteryRecords];
  }

  async getWeakConcepts(limit: number = 3): Promise<ConceptMastery[]> {
    const all = await this.getAllConceptMasteries();
    return all
      .filter((m) => m.currentMastery < 0.50)
      .sort((a, b) => a.currentMastery - b.currentMastery)
      .slice(0, limit);
  }

  async getStrongConcepts(limit: number = 3): Promise<ConceptMastery[]> {
    const all = await this.getAllConceptMasteries();
    return all
      .filter((m) => m.currentMastery >= 0.70)
      .sort((a, b) => b.currentMastery - a.currentMastery)
      .slice(0, limit);
  }

  async getSubjectProgress(): Promise<SubjectProgressSummary[]> {
    if (!apiConfig.useMock) {
      try {
        const masterySum = await api.get<any>('/mastery/me/subject/1');
        if (masterySum && typeof masterySum.total_concepts === 'number') {
          const avgMastery = Math.round((masterySum.average_mastery || 0.30) * 100);
          return [
            {
              subjectId: 1,
              subjectCode: masterySum.subject_code || 'MATH101',
              subjectName: masterySum.subject_name || 'Calculus I & Real Analysis',
              totalConcepts: masterySum.total_concepts,
              masteredCount: masterySum.mastered_count || 0,
              inProgressCount: masterySum.in_progress_count || 0,
              weakCount: masterySum.not_started_count || 0,
              averageMastery: avgMastery,
              colorScheme: 'electric',
            },
            {
              subjectId: 2,
              subjectCode: 'MATH201',
              subjectName: 'Linear Algebra & Vectors',
              totalConcepts: 12,
              masteredCount: 3,
              inProgressCount: 6,
              weakCount: 3,
              averageMastery: 54,
              colorScheme: 'cyan',
            },
            {
              subjectId: 3,
              subjectCode: 'CS102',
              subjectName: 'Data Structures & Algorithms',
              totalConcepts: 20,
              masteredCount: 7,
              inProgressCount: 10,
              weakCount: 3,
              averageMastery: 62,
              colorScheme: 'purple',
            },
          ];
        }
      } catch (err) {
        console.warn('ProgressService.getSubjectProgress live call failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    return [
      {
        subjectId: 1,
        subjectCode: 'MATH101',
        subjectName: 'Calculus I & Real Analysis',
        totalConcepts: 16,
        masteredCount: 4,
        inProgressCount: 9,
        weakCount: 3,
        averageMastery: 68,
        colorScheme: 'electric',
      },
      {
        subjectId: 2,
        subjectCode: 'MATH201',
        subjectName: 'Linear Algebra & Vectors',
        totalConcepts: 12,
        masteredCount: 3,
        inProgressCount: 6,
        weakCount: 3,
        averageMastery: 54,
        colorScheme: 'cyan',
      },
      {
        subjectId: 3,
        subjectCode: 'CS102',
        subjectName: 'Data Structures & Algorithms',
        totalConcepts: 20,
        masteredCount: 7,
        inProgressCount: 10,
        weakCount: 3,
        averageMastery: 62,
        colorScheme: 'purple',
      },
    ];
  }

  async getConceptGraph(subjectId: number = 1): Promise<ConceptGraphData> {
    if (!apiConfig.useMock) {
      try {
        const [graphRes, masterySum] = await Promise.all([
          api.get<any>(`/graph/subject/${subjectId}`),
          api.get<any>(`/mastery/me/subject/${subjectId}`).catch(() => null),
        ]);

        if (graphRes && Array.isArray(graphRes.nodes)) {
          const masteryMap = new Map<number, number>();
          if (masterySum && Array.isArray(masterySum.concepts)) {
            masterySum.concepts.forEach((c: any) => {
              masteryMap.set(c.concept_id, c.mastery_probability);
            });
          }

          const nodes = graphRes.nodes.map((n: any, idx: number) => {
            const prob = masteryMap.get(n.id) ?? n.mastery_probability ?? 0.20;
            return {
              id: n.id,
              conceptCode: n.concept_code || n.code || `C${n.id}`,
              name: n.name,
              difficultyLevel: (n.difficulty_level || 'beginner').toLowerCase() as any,
              subjectId: n.subject_id || subjectId,
              chapterId: n.chapter_id || 1,
              masteryProbability: Number(prob.toFixed(2)),
              status: prob >= 0.90 ? ('mastered' as const) : prob >= 0.40 ? ('ready' as const) : ('in_progress' as const),
              tierLevel: idx < 2 ? 0 : idx < 5 ? 1 : 2,
            };
          });

          const edges = (graphRes.edges || []).map((e: any) => ({
            fromConceptId: e.prerequisite_id,
            toConceptId: e.concept_id,
            relationshipType: 'strict' as const,
          }));

          return {
            subjectId,
            nodes,
            edges,
          };
        }
      } catch (err) {
        console.warn('ProgressService.getConceptGraph live call failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    const updatedNodes = mockConceptGraph.nodes.map((node) => {
      const match = mockMasteryRecords.find((m) => m.conceptId === node.id);
      if (match) {
        return {
          ...node,
          masteryProbability: match.currentMastery,
          status:
            match.currentMastery >= 0.90
              ? ('mastered' as const)
              : match.currentMastery >= 0.40
              ? ('ready' as const)
              : ('in_progress' as const),
        };
      }
      return node;
    });

    return {
      ...mockConceptGraph,
      subjectId,
      nodes: updatedNodes,
    };
  }

  async getActivityTrend(): Promise<ActivitySummary[]> {
    await simulateDelay();
    return [...mockActivityHistory];
  }

  async getLearningRecommendations(): Promise<LearningRecommendation[]> {
    await simulateDelay();
    return [...mockRecommendations];
  }
}

export const progressService = new ProgressService();
