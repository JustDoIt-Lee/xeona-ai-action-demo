"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';

interface AnalysisResult {
  filename: string;
  title: string;
  summary: string;
  keywords: Array<{
    text: string;
    count: number;
    context: string[];
  }>;
  mainTopics: string[];
  recommendations: string[];
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(true);
  const [selectedKeyword, setSelectedKeyword] = useState<{text: string; context: string[]} | null>(null);

  // ESC 키 처리
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedKeyword(null);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile);
      setResult(null); // 기존 결과 초기화
      handleFileUpload(droppedFile);
    } else {
      setError('PDF 파일만 업로드 가능합니다.');
    }
  };

  const handleFileUpload = async (uploadedFile: File) => {
    setIsAnalyzing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        withCredentials: true,
      });
      setResult(response.data);
      setShowUpload(false);
    } catch (err) {
      setError('문서 분석 중 오류가 발생했습니다.');
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-extrabold text-gray-900 mb-6 tracking-tight">
            PDF 문서 분석기
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            PDF 파일을 업로드하면 AI가 문서를 분석하여 주요 내용을 요약해드립니다.
          </p>
        </div>

        {/* Upload Area */}
        <div
          className={`border-3 border-dashed rounded-xl p-16 text-center transition-all duration-300
            ${isDragging ? 'border-blue-500 bg-blue-50 scale-102' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/30'}
            ${showUpload ? 'cursor-pointer shadow-sm hover:shadow-md' : 'hidden'}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput')?.click()}
        >
          <input
            type="file"
            id="fileInput"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) {
                // 파일 선택이 취소된 경우
                return;
              }
              if (file.type === 'application/pdf') {
                setFile(file);
                setResult(null); // 기존 결과 초기화
                handleFileUpload(file);
              } else {
                setError('PDF 파일만 업로드 가능합니다.');
              }
            }}
          />
          {isAnalyzing ? (
            <div className="text-gray-600">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-gray-900 mx-auto mb-4"></div>
              문서 분석 중...
            </div>
          ) : (
            <div className="text-gray-600">
              <svg className="mx-auto h-12 w-12 mb-4 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-lg mb-4">PDF 파일을 여기에 드래그하거나</p>
              <button className="bg-white text-blue-600 border-2 border-blue-600 px-6 py-3 rounded-xl text-lg font-semibold
                hover:bg-blue-50/50 transform transition-all duration-200 
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                shadow-sm hover:shadow-md">
                PDF 파일 선택하기
              </button>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Analysis Results */}
        {result && (
          <div className="mt-12 bg-white shadow-lg rounded-xl p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-gray-900 truncate max-w-[70%]">{result.title}</h2>
              <button
                onClick={() => { 
                  setFile(null); 
                  setShowUpload(true);
                  document.getElementById('fileInput')?.click();
                }}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-base font-semibold
                  hover:bg-blue-700 transform transition-all duration-200
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                  shadow-md hover:shadow-lg whitespace-nowrap"
              >
                새 문서 분석하기
              </button>
            </div>
            <div className="h-px bg-gray-200 mb-8"></div>
            
            <div className="grid gap-6">
              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                <h3 className="text-xl font-semibold mb-4 text-gray-800">문서 요약</h3>
                <p className="text-gray-700 text-lg leading-relaxed">{result.summary}</p>
              </div>

              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                <h3 className="text-xl font-semibold mb-4 text-gray-800">주요 키워드</h3>
                <div className="flex flex-wrap gap-2">
                  {result.keywords.map((keyword, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedKeyword(keyword)}
                      className="bg-blue-50/80 px-4 py-2 rounded-lg text-blue-700 font-medium text-base
                        hover:bg-blue-100 cursor-pointer transition-all duration-200 hover:scale-105"
                    >
                      {keyword.text} ({keyword.count})
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                <h3 className="text-xl font-semibold mb-4 text-gray-800">주요 내용</h3>
                <ul className="space-y-3">
                  {result.mainTopics.map((topic, idx) => (
                    <li key={idx} className="text-gray-700 text-lg flex items-start">
                      <span className="mr-3 text-blue-500">•</span>
                      {topic}
                    </li>
                  ))}
                </ul>
              </div>

              {result.recommendations.length > 0 && (
                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">추천사항</h3>
                  <ul className="space-y-3">
                    {result.recommendations.map((rec, idx) => (
                      <li key={idx} className="text-gray-700 text-lg flex items-start">
                        <span className="mr-3 text-blue-500">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            </div>

            {/* 하단 버튼 제거 - 상단으로 이동됨 */}
          </div>
        )}

        {/* Keyword Context Modal */}
        {selectedKeyword && (
          <div 
            className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50 backdrop-blur-sm"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setSelectedKeyword(null);
              }
            }}
          >
            <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 shadow-2xl transform transition-all flex flex-col max-h-[90vh]">
              {/* Modal Header */}
              <div className="px-7 py-5 flex items-center justify-between bg-gradient-to-r from-blue-50 via-blue-50 to-white rounded-t-2xl flex-shrink-0 border-b border-blue-100 shadow-sm">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-800">
                    문맥 속 키워드
                  </h3>
                  <p className="text-blue-600 font-medium mt-2">
                    &ldquo;{selectedKeyword.text}&rdquo; ({selectedKeyword.context.length}개의 문맥)
                  </p>
                </div>
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-blue-50/80 rounded-lg -mr-1"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto rounded-b-2xl bg-gradient-to-b from-gray-50 to-white
                [&::-webkit-scrollbar]:hidden">
                <div className="space-y-3 p-6">
                  {selectedKeyword.context.map((context, idx) => (
                    <div key={idx} className="group">
                      <div className="p-4 bg-white border-l-4 border-l-blue-400 border-t border-r border-b border-gray-200
                        rounded-lg shadow-sm hover:shadow-md transition-all duration-200 hover:border-l-blue-500">
                        <p className="text-gray-700 text-base leading-relaxed">
                          {context.split(new RegExp(`(${selectedKeyword.text})`, 'gi')).map((part, i) => 
                            part.toLowerCase() === selectedKeyword.text.toLowerCase() ? (
                              <span key={i} className="font-bold text-blue-600 bg-blue-50 px-1 rounded">{part}</span>
                            ) : (
                              part
                            )
                          )}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
