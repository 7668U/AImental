const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
const { getResultSectionTitles } = require('./utils/assessment-display.js');
const {
  isVipQuotaExhaustedError,
  showVipQuotaModal,
} = require('../utils/vip-quota.js');
// pages/assessment/result.js (渐变条 + 文字标签最终版)

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;
const DRINK_TI_ASSET_BASE = 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/drink-ti';
const SOUL_DRINK_RESULT_CARDS = {
  STJ: `${DRINK_TI_ASSET_BASE}/result-cards/stj-unsweetened-oolong-tea.jpg`,
  STP: `${DRINK_TI_ASSET_BASE}/result-cards/stp-lime-electrolyte-water.jpg`,
  SFJ: `${DRINK_TI_ASSET_BASE}/result-cards/sfj-hot-milk-tea.jpg`,
  SFP: `${DRINK_TI_ASSET_BASE}/result-cards/sfp-peach-sparkling-water.jpg`,
  NTJ: `${DRINK_TI_ASSET_BASE}/result-cards/ntj-cold-brew-black-coffee.jpg`,
  NTP: `${DRINK_TI_ASSET_BASE}/result-cards/ntp-special-cocktail.jpg`,
  NFJ: `${DRINK_TI_ASSET_BASE}/result-cards/nfj-honey-grapefruit-tea.jpg`,
  NFP: `${DRINK_TI_ASSET_BASE}/result-cards/nfp-colorful-fruit-tea.jpg`
};
const HEALTH_AI_SHORT_NAMES = new Set([
  'SDS',
  'BDI-II',
  'SAS',
  'BRMS',
  'SAD',
  'IAS',
  'Lonely',
  'DLS'
]);

Page({
  data: {
    isLoading: true,
    source: '',
    result: null,
    totalScore: 0,
    scoreSegments: [], // ✅ 【已加回】重新启用此数据，用于生成文字标签
    pointerPosition: 0,
    pointerLabelAlign: 'center',
    scoreMarkers: [],
    aiAnalysis: null,
    standardAnalysisSections: [],
    aiAnalysisSections: [],
    analysisBlocks: [],
    canGenerateAiAnalysis: false,
    hasCachedAiAnalysis: false,
    aiAnalysisLoaded: false,
    isAiAnalysisLoading: false,
    primaryCareer: null,
    recommendedCareers: [],
    secondaryProfile: null,
    talentRadarReport: null,
    fortuneReport: null,
    isSoulDrinkResult: false,
    soulDrinkResultCardUrl: '',
  },

  onLoad(options) {
    if (options.from) {
      this.setData({ source: options.from });
    }

    if (options.record_id) {
      this.fetchResultById(options.record_id);
    } else if (options.data) {
      try {
        const resultData = JSON.parse(decodeURIComponent(options.data));
        this.processAndRender(resultData);
      } catch (e) {
        console.error("解析初次结果数据失败", e);
        this.showErrorAndGoBack('结果加载失败');
      }
    } else {
      this.showErrorAndGoBack('无效的访问');
    }
  },

  fetchResultById(recordId) {
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/${recordId}`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.processAndRender(res.data);
        } else {
          console.error("获取历史详情失败", res);
          this.showErrorAndGoBack('加载历史详情失败');
        }
      },
      fail: (err) => {
        console.error("请求历史详情失败", err);
        this.showErrorAndGoBack('网络请求失败');
      }
    });
  },
  
  processAndRender(resultData) {
    console.log("--- 接收到的测评结果数据 (resultData) ---", resultData);
    const normalizedResult = this.normalizeResultData(resultData);
    const isSoulDrinkResult = normalizedResult?.scale_details?.short_name === 'SOUL-DRINK'
      || normalizedResult?.scale_info?.short_name === 'SOUL-DRINK';
    const soulDrinkResultCardUrl = isSoulDrinkResult
      ? this.getSoulDrinkResultCardUrl(normalizedResult)
      : '';
    const cachedAiAnalysis = this.normalizeAiAnalysis(resultData);
    const standardAnalysisSections = this.buildFallbackAnalysisSections(normalizedResult);
    const canGenerateAiAnalysis = this.canGenerateAiAnalysisForResult(normalizedResult);
    const primaryCareer = normalizedResult?.result_details?.primary_career || null;
    const recommendedCareers = Array.isArray(normalizedResult?.result_details?.recommended_careers)
      ? normalizedResult.result_details.recommended_careers
      : [];
    const secondaryProfile = normalizedResult?.result_details?.secondary_title
      ? {
          title: normalizedResult.result_details.secondary_title,
          description: normalizedResult.result_details.secondary_description || '',
          recommendation: normalizedResult.result_details.secondary_recommendation || '',
          inRelationships: normalizedResult.result_details.secondary_in_relationships || '',
          underStress: normalizedResult.result_details.secondary_under_stress || '',
          facingChange: normalizedResult.result_details.secondary_facing_change || '',
        }
      : null;
    const talentRadarReport = normalizedResult?.scale_details?.short_name === 'AGLT'
      ? this.buildTalentRadarReport(normalizedResult)
      : null;
    const fortuneReport = normalizedResult?.scale_details?.short_name === 'RFLT'
      ? this.buildFortuneReport(normalizedResult)
      : null;
    this.setData({
      result: normalizedResult,
      aiAnalysis: cachedAiAnalysis,
      standardAnalysisSections,
      aiAnalysisSections: [],
      analysisBlocks: this.buildAnalysisBlocks(standardAnalysisSections, []),
      canGenerateAiAnalysis,
      hasCachedAiAnalysis: !!cachedAiAnalysis,
      aiAnalysisLoaded: false,
      isAiAnalysisLoading: false,
      primaryCareer,
      recommendedCareers,
      secondaryProfile,
      talentRadarReport,
      fortuneReport,
      isSoulDrinkResult,
      soulDrinkResultCardUrl
    });
    
    const type = normalizedResult?.scale_details?.assessment_type;

    if (type === 'scoring') {
      const jsonData = normalizedResult.scale_details.json_data;
      const interpretations = jsonData.interpretations || [];
      
      if (interpretations.length === 0) {
        this.showErrorAndGoBack('问卷分数段未定义');
        return;
      }

      const userScore = normalizedResult.final_score;
      
      const minPossibleScore = interpretations[0].min_score;
      const maxPossibleScore = interpretations[interpretations.length - 1].max_score;
      const totalScorableRange = maxPossibleScore - minPossibleScore;

      if (totalScorableRange <= 0) {
        this.showErrorAndGoBack('问卷分数范围无效');
        return;
      }
      
      // ✅ 【核心修改已集成】重新计算 scoreSegments 用于生成文字标签
// ✅ 这是新的 JS 代码
// ✅ 这是最终正确的 JS 代码，请用它替换
const scoreSegments = interpretations.map(interp => {
  // 根据每个区间自己的 min_score 计算它的起始位置
  const left = ((interp.min_score - minPossibleScore) / totalScorableRange) * 100;

  // 根据每个区间自己的 max_score 和 min_score 的差值计算它的宽度
  const width = ((interp.max_score - interp.min_score) / totalScorableRange) * 100;

  return {
    level: interp.level,
    width: width,
    left: left
  };
});

      const numericUserScore = Number(userScore);
      const safeUserScore = Number.isFinite(numericUserScore) ? numericUserScore : minPossibleScore;
      const pointerPosition = this.clampPercent(((safeUserScore - minPossibleScore) / totalScorableRange) * 100);

      let pointerLabelAlign = 'center';
      if (pointerPosition > 85) pointerLabelAlign = 'left';
      else if (pointerPosition < 15) pointerLabelAlign = 'right';

      const scoreMarkers = [];
      for (let i = 0; i < interpretations.length - 1; i++) {
        const interp = interpretations[i];
        scoreMarkers.push({
          score: interp.max_score,
          position: ((interp.max_score - minPossibleScore) / totalScorableRange) * 100
        });
      }

      this.setData({
        totalScore: maxPossibleScore,
        scoreSegments: scoreSegments, // ✅ 【已加回】将计算好的标签数据传给WXML
        pointerPosition: pointerPosition,
        pointerLabelAlign: pointerLabelAlign,
        scoreMarkers: scoreMarkers,
        isLoading: false
      });

    } else if (type === 'categorical') {
      this.setData({
        isLoading: false
      });
    } else {
      console.error("无法识别的结果类型", resultData);
      this.showErrorAndGoBack('结果类型无法识别');
    }
  },

  clampPercent(value) {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(100, value));
  },

  normalizeResultData(resultData) {
    if (!resultData) return resultData;

    const normalized = { ...resultData };
    const isEmptyLevel = normalized.result_level === null
      || normalized.result_level === undefined
      || String(normalized.result_level).trim() === ''
      || String(normalized.result_level).trim().toLowerCase() === 'null';

    if (isEmptyLevel) {
      normalized.result_level = '结果待确认';
    }

    if (!normalized.scale_info && !normalized.scale_details) {
      const assessmentType = normalized.final_score !== null && normalized.final_score !== undefined
        ? 'scoring'
        : 'categorical';
      const legacyScale = {
        id: normalized.scale_id || `legacy-${normalized.id || 'record'}`,
        short_name: 'LEGACY',
        name: '历史测评',
        description: '该记录对应的量表定义已不在当前量表目录中。',
        category: '历史记录',
        assessment_type: assessmentType
      };
      normalized.scale_info = legacyScale;
      normalized.scale_details = legacyScale;
    } else if (!normalized.scale_details && normalized.scale_info) {
      normalized.scale_details = normalized.scale_info;
    } else if (!normalized.scale_info && normalized.scale_details) {
      normalized.scale_info = normalized.scale_details;
    }

    if (normalized.final_score !== null && normalized.final_score !== undefined) {
      const numericScore = Number(normalized.final_score);
      normalized.final_score = Number.isFinite(numericScore)
        ? Math.round(numericScore * 100) / 100
        : normalized.final_score;
    }

    return normalized;
  },

  getSoulDrinkResultCardUrl(resultData) {
    const details = resultData?.result_details || {};
    const directUrl = details.result_card_url || details.resultCardUrl || details.result_card_image_url;
    if (directUrl) {
      return this.resolveAssetUrl(directUrl);
    }

    const typeCode = details.type_code || details.typeCode || resultData?.result_type || '';
    const mappedUrl = SOUL_DRINK_RESULT_CARDS[String(typeCode).toUpperCase()];
    if (mappedUrl) {
      return this.resolveAssetUrl(mappedUrl);
    }

    return this.resolveAssetUrl(details.image_url || '');
  },

  resolveAssetUrl(url) {
    if (!url) return '';
    const normalizedUrl = String(url);
    if (/^https?:\/\//.test(normalizedUrl)) return normalizedUrl;
    return `${SERVER_BASE_URL}${normalizedUrl.startsWith('/') ? '' : '/'}${normalizedUrl}`;
  },

  canGenerateAiAnalysisForResult(resultData) {
    if (!resultData || !resultData.id) return false;
    const scaleMeta = resultData.scale_details || resultData.scale_info || {};
    return scaleMeta.category === '心理健康'
      || scaleMeta.display_group === '心理健康'
      || HEALTH_AI_SHORT_NAMES.has(scaleMeta.short_name);
  },

  buildAnalysisBlocks(standardSections, aiSections) {
    const blocks = [];
    if (Array.isArray(standardSections) && standardSections.length > 0) {
      blocks.push({
        key: 'standard',
        title: '结果分析',
        sections: standardSections
      });
    }
    if (Array.isArray(aiSections) && aiSections.length > 0) {
      blocks.push({
        key: 'ai',
        title: 'AI深度分析',
        sections: aiSections
      });
    }
    return blocks;
  },

  showAiAnalysis(aiAnalysis) {
    const aiSections = this.buildAiAnalysisSections(aiAnalysis);
    if (aiSections.length === 0) {
      wx.showToast({ title: 'AI深度分析内容暂时为空', icon: 'none' });
      return;
    }

    this.setData({
      aiAnalysis,
      aiAnalysisSections: aiSections,
      analysisBlocks: this.buildAnalysisBlocks(this.data.standardAnalysisSections, aiSections),
      hasCachedAiAnalysis: true,
      aiAnalysisLoaded: true
    });
  },

  handleGenerateAiAnalysis() {
    if (this.data.isAiAnalysisLoading || !this.data.canGenerateAiAnalysis) return;

    if (this.data.aiAnalysis) {
      this.showAiAnalysis(this.data.aiAnalysis);
      return;
    }

    const recordId = this.data.result?.id;
    if (!recordId) {
      wx.showToast({ title: '测评记录信息不完整', icon: 'none' });
      return;
    }

    this.setData({ isAiAnalysisLoading: true });
    const requestId = `assessment-ai-${recordId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/${recordId}/ai-analysis`,
      method: 'POST',
      timeout: 120000,
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'X-Request-ID': requestId
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data?.ai_analysis) {
          this.showAiAnalysis(res.data.ai_analysis);
          return;
        }

        const error = {
          statusCode: res.statusCode,
          data: res.data
        };
        if (isVipQuotaExhaustedError(error)) {
          showVipQuotaModal({ error, feature: 'assessment_analysis' });
          return;
        }

        const detail = res.data?.detail;
        const message = typeof detail === 'string'
          ? detail
          : (detail?.message || 'AI深度分析生成失败，请稍后重试');
        wx.showToast({ title: message, icon: 'none', duration: 3000 });
      },
      fail: () => {
        wx.showToast({ title: '网络请求失败，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ isAiAnalysisLoading: false });
      }
    });
  },

  normalizeAiAnalysis(resultData) {
    const detailsAnalysis = resultData?.result_details?.ai_analysis;
    return resultData?.ai_analysis || detailsAnalysis || null;
  },

  buildAiAnalysisSections(aiAnalysis) {
    if (!aiAnalysis) return [];

    const sections = [];

    if (aiAnalysis.state_summary) {
      sections.push({
        key: 'state',
        title: '当前状态',
        type: 'text',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-sun.png',
        text: aiAnalysis.state_summary
      });
    }

    if (Array.isArray(aiAnalysis.dimensions) && aiAnalysis.dimensions.length > 0) {
      sections.push({
        key: 'dimensions',
        title: '主要影响维度',
        type: 'dimensions',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-ai.png',
        dimensions: aiAnalysis.dimensions.map(item => ({
          ...item,
          evidenceText: Array.isArray(item.evidence) ? item.evidence.join('、') : ''
        }))
      });
    }

    if (Array.isArray(aiAnalysis.possible_causes) && aiAnalysis.possible_causes.length > 0) {
      sections.push({
        key: 'causes',
        title: '可能相关原因',
        type: 'list',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-ai.png',
        list: aiAnalysis.possible_causes
      });
    }

    if (Array.isArray(aiAnalysis.small_actions) && aiAnalysis.small_actions.length > 0) {
      sections.push({
        key: 'actions',
        title: '可以先试试',
        type: 'list',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-sun.png',
        list: aiAnalysis.small_actions
      });
    }

    const support = aiAnalysis.professional_support;
    if (support && support.text) {
      sections.push({
        key: 'support',
        title: '专业支持',
        type: 'support',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-ai.png',
        recommended: !!support.recommended,
        urgency: support.urgency || '',
        text: support.text
      });
    }

    const recording = aiAnalysis.emotion_recording;
    if (recording && recording.text) {
      sections.push({
        key: 'recording',
        title: '持续记录',
        type: 'recording',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-sun.png',
        recommended: !!recording.recommended,
        focusText: Array.isArray(recording.focus) ? recording.focus.join('、') : '',
        text: recording.text
      });
    }

    const riskNote = aiAnalysis.risk_note;
    if (riskNote && riskNote.triggered && riskNote.text) {
      sections.unshift({
        key: 'risk',
        title: '安全提醒',
        type: 'risk',
        bgIcon: '',
        level: riskNote.level || '',
        text: riskNote.text
      });
    }

    return sections;
  },

  buildFallbackAnalysisSections(resultData) {
    if (!resultData) return [];

    const sections = [];
    const sectionTitles = getResultSectionTitles(
      resultData?.scale_details?.short_name,
      resultData?.scale_details?.assessment_type
    );
    const interpretation = typeof resultData.result_interpretation === 'string'
      ? resultData.result_interpretation.trim()
      : '';
    const recommendation = typeof resultData.result_recommendation === 'string'
      ? resultData.result_recommendation.trim()
      : '';
    const detailItems = this.buildResultDetailItems(resultData.result_details);

    if (detailItems.length > 0) {
      sections.push({
        key: 'details',
        title: '维度得分',
        type: 'details',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-ai.png',
        detailItems: detailItems
      });
    }

    if (interpretation) {
      sections.push({
        key: 'interpretation',
        title: sectionTitles.interpretation,
        type: 'text',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-ai.png',
        text: interpretation
      });
    }

    if (recommendation) {
      sections.push({
        key: 'recommendation',
        title: sectionTitles.recommendation,
        type: 'text',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-sun.png',
        text: recommendation
      });
    }

    if (sections.length === 0) {
      const level = typeof resultData.result_level === 'string' ? resultData.result_level.trim() : '';
      const score = resultData.final_score ?? resultData.raw_score;
      sections.push({
        key: 'generated',
        title: '结果说明',
        type: 'text',
        bgIcon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/result/section-sun.png',
        text: level && level !== '结果待确认'
          ? `本次结果为“${level}”。你可以先把它作为一次自我观察，结合最近的真实状态继续留意变化。`
          : `本次结果已生成，得分为 ${score ?? '当前分数'}。暂未匹配到完整解读，请稍后从历史测评中再次查看。`
      });
    }

    return sections;
  },

  buildResultDetailItems(resultDetails) {
    if (!resultDetails || Array.isArray(resultDetails) || typeof resultDetails !== 'object') {
      return [];
    }

    const labelMap = {
      anxiety_score: '焦虑得分',
      avoidance_score: '回避得分',
      安全型: '安全型得分',
      焦虑型: '焦虑型得分',
      回避型: '回避型得分',
      I: '内向倾向（I）',
      E: '外向倾向（E）',
      S: '感觉倾向（S）',
      N: '直觉倾向（N）',
      T: '思考倾向（T）',
      F: '情感倾向（F）',
      J: '判断倾向（J）',
      P: '感知倾向（P）'
    };
    const allowedDimensionKeys = new Set([
      'anxiety_score',
      'avoidance_score',
      '安全型',
      '焦虑型',
      '回避型',
      'I',
      'E',
      'S',
      'N',
      'T',
      'F',
      'J',
      'P'
    ]);

    const items = [];
    const appendNumericItem = (key, value) => {
      if (!allowedDimensionKeys.has(key)) return;
      if (typeof value !== 'number' || !Number.isFinite(value)) return;

      items.push({
        label: labelMap[key] || key,
        value: String(Math.round(value * 100) / 100)
      });
    };

    Object.entries(resultDetails.dimension_scores || {}).forEach(([key, value]) => {
      appendNumericItem(key, value);
    });

    Object.entries(resultDetails).forEach(([key, value]) => {
      if (key === 'dimension_scores') return;
      appendNumericItem(key, value);
    });

    return items.slice(0, 8);
  },

  buildTalentRadarReport(resultData) {
    const details = resultData?.result_details || {};
    const breakdown = Array.isArray(details.tendency_breakdown) ? details.tendency_breakdown : [];
    const scoreItems = breakdown.slice(0, 8).map(item => ({
      label: item.title,
      value: item.count,
      ratio: Math.round((item.ratio || 0) * 100)
    }));

    return {
      primaryTitle: details.primary_title || resultData.result_level || '',
      primaryTagline: details.primary_tagline || '',
      primarySummary: details.primary_summary || '',
      primaryBestScene: details.primary_best_scene || '',
      primaryGrowthFocus: details.primary_growth_focus || '',
      pairSummary: details.pair_summary || '',
      secondaryTitle: details.secondary_title || '',
      secondaryDescription: details.secondary_description || '',
      secondaryTagline: details.secondary_tagline || '',
      latentTitle: details.latent_title || '',
      latentDescription: details.latent_description || '',
      latentTagline: details.latent_tagline || '',
      latentBridge: details.latent_bridge || '',
      stressTitle: details.stress_title || '',
      stressSummary: details.stress_summary || details.stress_description || '',
      radarSummary: details.radar_summary || '',
      latentSummary: details.latent_summary || '',
      scoreItems
    };
  },

  buildFortuneReport(resultData) {
    const details = resultData?.result_details || {};
    return {
      title: resultData.result_level || '',
      keyword: details.fortune_keyword || '',
      window: details.fortune_window || '',
      luckyColor: details.lucky_color || '',
      luckyAction: details.lucky_action || '',
      luckyPhrase: details.lucky_phrase || '',
      emotionalAnchor: details.emotional_anchor || '',
      interpretation: resultData.result_interpretation || '',
      recommendation: resultData.result_recommendation || '',
      relationship: details.in_relationships || '',
      stress: details.under_stress || '',
      change: details.facing_change || ''
    };
  },

  handleConfirm() {
    if (this.data.source === 'history') {
      wx.navigateBack();
    } else {
      wx.reLaunch({
        url: '/pages/assessment/index'
      });
    }
  },

  showErrorAndGoBack(title) {
    wx.showToast({
      title: title,
      icon: 'error',
      duration: 2000
    });
    
    setTimeout(() => {
      if (getCurrentPages().length > 1) {
        wx.navigateBack();
      } else {
        wx.reLaunch({
          url: '/pages/assessment/index'
        });
      }
    }, 2000);
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
