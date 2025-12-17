# 🧪 End-to-End Testing Guide: Actionable Recommendations

## 📋 Overview

This guide provides comprehensive manual testing instructions for the Actionable Recommendations feature.

## 🚀 Prerequisites

1. Backend server running on http://localhost:8000
2. Frontend server running on http://localhost:5173
3. Valid user account
4. Project with at least 10-15 user stories

## 🔧 Setup Test Data

### Option 1: Use Existing Project
If you already have a project with stories, you can use it for testing.

### Option 2: Create Fresh Test Project
1. Login to the application
2. Create a new project: "Test Actionable Recommendations"
3. Add description: "Testing AI recommendations feature"
4. Create the project

## 🎯 Test Cases

### Test Case 1: Generate Recommendations (Full Analysis)

**Purpose**: Verify that recommendations are generated and displayed

**Steps**:
1. Open your test project
2. Click the "📊 Анализ карты" button in the top toolbar
3. The Analysis Panel modal should open
4. Click on "🎯 Полный анализ" tab (should be selected by default)
5. Wait for analysis to complete (~5-10 seconds)

**Expected Results**:
- Analysis completes without errors
- If there are issues, you should see a section titled "✨ Рекомендуемые действия"
- Each recommendation shows:
  - Title
  - Description
  - Severity indicator (color-coded)
  - Impact description
  - "Применить" button
  - Story count indicator

**Pass Criteria**:
✅ Recommendations appear
✅ All fields are populated
✅ No console errors

---

### Test Case 2: ADD_DESCRIPTION Recommendation

**Purpose**: Test AI-powered description generation

**Setup**:
1. Create or find 3+ stories WITHOUT descriptions
2. Leave only the title field filled

**Steps**:
1. Run Full Analysis ("🎯 Полный анализ")
2. Wait for analysis to complete
3. Find the recommendation: "Добавить описания к X историям"
4. Click the "Применить" button
5. Wait for the operation to complete (~30 seconds for 3 stories)

**Expected Results**:
- Button shows "Применение..." with spinner during processing
- Success message appears: "Добавлено описание к X историям"
- Analysis automatically re-runs
- Affected stories now have descriptions
- Recommendation disappears from the list (or count decreases)

**Verification**:
1. Open each affected story
2. Verify description field is now filled
3. Verify description is relevant to the story title

**Pass Criteria**:
✅ Descriptions added successfully
✅ AI-generated descriptions are relevant
✅ Success notification shown
✅ Auto-refresh works

---

### Test Case 3: ADD_CRITERIA Recommendation

**Purpose**: Test AI-powered acceptance criteria generation

**Setup**:
1. Create or find 3+ stories WITHOUT acceptance criteria
2. Stories should have descriptions but no AC

**Steps**:
1. Run Full Analysis
2. Find recommendation: "Добавить acceptance criteria к X историям"
3. Click "Применить"
4. Wait for completion (~30 seconds)

**Expected Results**:
- Success message: "Добавлены acceptance criteria к X историям"
- Affected stories now have AC
- AC are specific and measurable

**Verification**:
1. Open each affected story
2. Verify acceptance criteria are present
3. Verify criteria are relevant and specific

**Pass Criteria**:
✅ AC added successfully
✅ Criteria are meaningful
✅ No duplicate or generic criteria

---

### Test Case 4: MERGE_STORIES Recommendation

**Purpose**: Test duplicate story merging

**Setup**:
1. Create 2 identical or very similar stories:
   - Story 1: "User login"
   - Story 2: "User authentication"
   - Both should have similar descriptions

**Steps**:
1. Run Full Analysis
2. Switch to "🔍 Схожесть" tab
3. Find recommendation: "Объединить X дубликатов"
4. Click "Применить"
5. Wait for completion (instant, no AI)

**Expected Results**:
- Success message: "Объединено X историй в 'Story Title'"
- Primary story retains all content
- Duplicate stories are deleted
- Content from duplicates is merged into primary

**Verification**:
1. Find the primary story
2. Verify it contains content from both stories
3. Verify duplicate is no longer visible

**Pass Criteria**:
✅ Stories merged correctly
✅ No content lost
✅ Duplicates removed

---

### Test Case 5: MOVE_STORY Recommendation (MVP Optimization)

**Purpose**: Test story movement between releases

**Setup**:
1. Create MVP release with 16+ stories
2. Create "Release 1" or later release

**Steps**:
1. Run Full Analysis
2. Find recommendation: "Оптимизировать MVP (X историй → ~10-12)"
3. Click "Применить"
4. Wait for completion (instant)

**Expected Results**:
- Success message: "Перемещено X историй из MVP в Release 1"
- MVP now has ~10-12 stories
- Remaining stories moved to next release

**Verification**:
1. Check MVP release - should have fewer stories
2. Check Release 1 - should have moved stories
3. Verify no stories were lost

**Pass Criteria**:
✅ Stories moved successfully
✅ MVP is more focused
✅ All stories accounted for

---

### Test Case 6: IMPROVE_STORY Recommendation

**Purpose**: Test comprehensive story improvement

**Setup**:
1. Create stories with minimal/poor quality content
2. Use vague descriptions or missing details

**Steps**:
1. Run Full Analysis
2. Find recommendation: "Улучшить X историй"
3. Click "Применить"
4. Wait for completion (~30 seconds per story)

**Expected Results**:
- Success message: "Улучшено X историй"
- Stories have improved descriptions and AC
- Content follows User Story best practices

**Verification**:
1. Review improved stories
2. Verify descriptions are clearer
3. Verify AC are more specific

**Pass Criteria**:
✅ Stories improved
✅ Quality increased
✅ No information lost

---

### Test Case 7: Error Handling

**Purpose**: Test error scenarios and recovery

**Test 7.1: Network Error**
1. Disconnect network
2. Try to apply recommendation
3. Verify error message appears
4. Reconnect and retry

**Test 7.2: Invalid Story IDs**
1. Delete stories manually
2. Try to apply recommendation for deleted stories
3. Verify graceful error handling

**Test 7.3: API Rate Limiting**
1. Apply multiple recommendations rapidly
2. Verify rate limiting works
3. Verify clear error message

**Pass Criteria**:
✅ Clear error messages
✅ No crashes
✅ User can retry

---

### Test Case 8: Combined Recommendations

**Purpose**: Test multiple recommendation sources

**Setup**:
Create a project with:
- 5 stories without descriptions
- 5 stories without AC
- 2 duplicate stories
- MVP with 18 stories

**Steps**:
1. Run Full Analysis
2. Verify recommendations from both validation and similarity appear
3. Apply recommendations in sequence
4. Verify each works correctly

**Expected Results**:
- All recommendation types appear
- Each can be applied independently
- Success messages for each
- Analysis refreshes after each apply

**Pass Criteria**:
✅ Multiple recommendations shown
✅ All work correctly
✅ No conflicts between types

---

### Test Case 9: Loading States

**Purpose**: Test UI feedback during operations

**Steps**:
1. Click "Применить" on any recommendation
2. Immediately observe the button state
3. Observe during AI processing
4. Observe after completion

**Expected Results**:
- Button shows "Применение..." with spinner
- Button is disabled during processing
- Button returns to normal after completion
- Loading spinner visible

**Pass Criteria**:
✅ Loading state visible
✅ Button disabled during process
✅ Clear visual feedback

---

### Test Case 10: Success Notification Auto-Hide

**Purpose**: Test notification behavior

**Steps**:
1. Apply any recommendation
2. Wait for success message
3. Observe for 2 seconds

**Expected Results**:
- Success message appears at top of panel
- Message includes recommendation result
- Message auto-hides after 2 seconds
- Analysis automatically refreshes

**Pass Criteria**:
✅ Message appears
✅ Auto-hides after ~2 seconds
✅ Auto-refresh triggered

---

## 🔍 Performance Testing

### Test Case 11: Batch Operations Performance

**Purpose**: Measure performance of batch operations

**Steps**:
1. Create 10 stories without descriptions
2. Generate ADD_DESCRIPTION recommendation
3. Time the operation
4. Verify all 10 stories updated

**Expected Results**:
- Operation completes in ~30-60 seconds
- No timeouts or errors
- All stories processed

**Acceptable Performance**:
- ≤10 stories: 30-60 seconds
- No memory leaks
- No browser freezing

---

## 📊 Test Results Template

```
Date: ___________
Tester: ___________
Environment: Local / Staging / Production

Test Case Results:
[ ] TC1: Generate Recommendations - Pass/Fail
[ ] TC2: ADD_DESCRIPTION - Pass/Fail
[ ] TC3: ADD_CRITERIA - Pass/Fail
[ ] TC4: MERGE_STORIES - Pass/Fail
[ ] TC5: MOVE_STORY - Pass/Fail
[ ] TC6: IMPROVE_STORY - Pass/Fail
[ ] TC7: Error Handling - Pass/Fail
[ ] TC8: Combined Recommendations - Pass/Fail
[ ] TC9: Loading States - Pass/Fail
[ ] TC10: Success Notification - Pass/Fail
[ ] TC11: Performance - Pass/Fail

Issues Found:
1. ___________
2. ___________
3. ___________

Notes:
___________
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Recommendations Not Appearing
**Solution**:
- Check that stories have actual issues (missing descriptions, etc.)
- Verify backend is running
- Check browser console for errors

### Issue 2: Apply Button Does Nothing
**Solution**:
- Check network tab for API errors
- Verify recommendation ID is valid
- Check backend logs

### Issue 3: AI Operations Timeout
**Solution**:
- Check Groq API key is configured
- Verify rate limits not exceeded
- Check backend logs for AI errors

### Issue 4: Stories Not Updated After Apply
**Solution**:
- Refresh the page manually
- Check if operation actually succeeded
- Verify backend database updated

---

## ✅ Final Checklist

Before marking feature as complete, verify:

- [ ] All 11 test cases pass
- [ ] No console errors during normal operation
- [ ] Performance is acceptable
- [ ] Error messages are user-friendly
- [ ] UI is responsive during operations
- [ ] Success notifications work correctly
- [ ] Auto-refresh works after apply
- [ ] Backend tests pass (15/15)
- [ ] No memory leaks
- [ ] Works in both Chrome and Firefox

---

## 📝 Testing Notes

### Quick Smoke Test (5 minutes)
If you only have 5 minutes, run this quick test:

1. Open project
2. Click "📊 Анализ карты"
3. Run "🎯 Полный анализ"
4. Verify recommendations appear
5. Apply one recommendation
6. Verify success message
7. Verify stories updated

### Full Test Suite (30 minutes)
Run all 11 test cases in order.

### Regression Test
After any changes to recommendation logic:
1. Run TC2 (ADD_DESCRIPTION)
2. Run TC3 (ADD_CRITERIA)
3. Run TC4 (MERGE_STORIES)
4. Run TC7 (Error Handling)

---

## 🔗 Related Documentation

- `ACTIONABLE_RECOMMENDATIONS.md` - Feature implementation details
- `backend/tests/test_recommendation_service.py` - Backend unit tests
- `frontend/src/AnalysisPanel.test.jsx` - Frontend component tests
