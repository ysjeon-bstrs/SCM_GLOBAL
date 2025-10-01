// Google Apps Script Web App 코드
// 이 코드를 Google Sheets의 Apps Script에 붙여넣고 웹앱으로 배포하세요

function _readSheet_(sheetId, tabName) {
  try {
    console.log("Opening spreadsheet with ID:", sheetId);
    var ss = SpreadsheetApp.openById(sheetId);
    console.log("Spreadsheet opened successfully");
    
    var sh = ss.getSheetByName(tabName);
    if (!sh) {
      console.log("Sheet not found:", tabName);
      return { ok:false, error:"no_sheet", tab: tabName, availableSheets: ss.getSheets().map(s => s.getName()) };
    }
    
    console.log("Sheet found:", tabName);
    var vals = sh.getDataRange().getValues();
    if (!vals || vals.length === 0) {
      console.log("No data in sheet");
      return { ok:true, tab:tabName, rows:[] };
    }
    
    var head = vals.shift();
    console.log("Headers:", head);
    
    // 객체화 (헤더 → 키)
    var rows = vals.map(function(r){
      var o = {};
      for (var i=0;i<head.length;i++){
        var k = String(head[i]||"").trim();
        if (!k) k = "col"+(i+1);
        o[k] = (i<r.length ? r[i] : "");
      }
      return o;
    });
    
    console.log("Processed rows:", rows.length);
    return { ok:true, tab:tabName, rows:rows };
  } catch (error) {
    console.log("Error in _readSheet_:", error);
    return { ok:false, error: error.toString(), sheetId: sheetId, tab: tabName };
  }
}

function doGet(e) {
  try {
    console.log("=== doGet function called ===");
    console.log("e object:", e);
    console.log("e type:", typeof e);
    
    // e 객체가 undefined인 경우 기본값으로 테스트
    if (!e) {
      console.log("e is undefined, testing with default values");
      // 기본값으로 테스트 실행
      var testResult = _readSheet_("1RYjKW2UDJ2kWJLAqQH26eqx2-r9Xb0_qE_hfwu9WIj8", "snap_정제");
      return ContentService.createTextOutput(
        JSON.stringify({ 
          ok: true, 
          message: "Testing with default values - WebApp is working!",
          result: testResult
        })
      ).setMimeType(ContentService.MimeType.JSON);
    }
    
    // e 객체가 있으면 파라미터 추출
    var params = e.parameter || {};
    console.log("e.parameter:", e.parameter);
    console.log("params:", params);
    
    // 필수 파라미터
    var sheetId = params.id || "";              // 스프레드시트 ID
    var tab     = params.sheet || "snap_정제";
    var token   = params.token || "";

    // 디버깅용 로그
    console.log("Final parameters:", { sheetId: sheetId, tab: tab, token: token });
    
    // sheetId가 없으면 에러
    if (!sheetId) {
      return ContentService.createTextOutput(
        JSON.stringify({ 
          ok: false, 
          error: "Missing sheet ID parameter",
          received: { sheetId: sheetId, tab: tab, token: token }
        })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // (선택) 초간단 토큰 검증 - 임시로 비활성화
    var EXPECT = "BOOSTERS_MINI_TOKEN_SCM_DASHBOARD_20250929";
    // if (token !== EXPECT) {
    //   console.log("Token mismatch. Expected:", EXPECT, "Got:", token);
    //   return ContentService.createTextOutput(
    //     JSON.stringify({ ok:false, error:"unauthorized", expected: EXPECT, got: token })
    //   ).setMimeType(ContentService.MimeType.JSON);
    // }

    var res = _readSheet_(sheetId, tab);
    console.log("Result:", res);
    return ContentService.createTextOutput(
      JSON.stringify(res)
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    console.log("Error:", error);
    return ContentService.createTextOutput(
      JSON.stringify({ ok:false, error: error.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
