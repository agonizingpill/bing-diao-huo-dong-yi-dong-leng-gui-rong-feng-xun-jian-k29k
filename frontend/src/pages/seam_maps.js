        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "带载融缝的邻域密度",
  "module": "融缝稠密程度",
  "caption": "融缝稠密程度",
  "detail": "将同格带载历史换成标准化特征，近邻越远说明当前形态越少见。试算版本与现用版本用同一批带载复检样本对照，漏报不增加且误报减少才可启用。",
  "path": "/seam_maps",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "sample",
      "label": "冰雕实测"
    },
    {
      "name": "density",
      "label": "局部相对密度"
    },
    {
      "name": "threshold",
      "label": "基线门槛"
    },
    {
      "name": "decision",
      "label": "人工复核指向"
    },
    {
      "name": "version",
      "label": "评分版本"
    },
    {
      "name": "token",
      "label": "计算凭据"
    }
  ],
  "extra": [
    {
      "caption": "评分版本",
      "path": "/seam_maps/versions",
      "view": "grid",
      "columns": [
        {
          "name": "code",
          "label": "版本"
        },
        {
          "name": "neighbors",
          "label": "近邻数"
        },
        {
          "name": "state",
          "label": "状态"
        }
      ]
    },
    {
      "caption": "带载复检结论",
      "path": "/seam_maps/rechecks",
      "view": "grid",
      "columns": [
        {
          "name": "code",
          "label": "编号"
        },
        {
          "name": "sample",
          "label": "冰雕实测"
        },
        {
          "name": "verdict",
          "label": "复检结论"
        }
      ]
    },
    {
      "caption": "试算对照",
      "path": "/seam_maps/trials",
      "view": "grid",
      "columns": [
        {
          "name": "code",
          "label": "编号"
        },
        {
          "name": "version",
          "label": "试算版本"
        },
        {
          "name": "base_version",
          "label": "对照现用版"
        },
        {
          "name": "samples",
          "label": "对照样本数"
        },
        {
          "name": "miss_current",
          "label": "现用漏报"
        },
        {
          "name": "miss_trial",
          "label": "试算漏报"
        },
        {
          "name": "false_current",
          "label": "现用误报"
        },
        {
          "name": "false_trial",
          "label": "试算误报"
        },
        {
          "name": "state",
          "label": "状态"
        }
      ]
    }
  ],
  "layout": "split",
  "view": "grid",
  "actions": [
    {
      "name": "score_seam",
      "label": "计算带载局部密度",
      "path": "/seam_maps/score-seam",
      "fields": [
        {
          "name": "sample",
          "label": "观测号",
          "kind": "text",
          "initial": "ICE-X"
        }
      ],
      "help": "密度基于近邻距离的反比，按现役版本近邻数计算。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "record_seam",
      "label": "复核融缝提示",
      "path": "/seam_maps/record-seam",
      "fields": [
        {
          "name": "code",
          "label": "融缝单号",
          "kind": "text",
          "initial": "DENS-24"
        },
        {
          "name": "token",
          "label": "计算凭据",
          "kind": "token",
          "initial": ""
        }
      ],
      "help": "将算法输出与本次冰雕关联，并记下所用评分版本。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "record_recheck",
      "label": "录入带载复检结论",
      "path": "/seam_maps/record-recheck",
      "fields": [
        {
          "name": "code",
          "label": "复检编号",
          "kind": "text",
          "initial": "RCK-24"
        },
        {
          "name": "sample",
          "label": "观测号",
          "kind": "text",
          "initial": "ICE-X"
        },
        {
          "name": "verdict",
          "label": "复检结论",
          "kind": "choice",
          "options": [
            "确需换格",
            "无需换格"
          ]
        }
      ],
      "help": "每条带载实测只留一份复检结论，作为对照基准。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "draft_version",
      "label": "登记试算版本",
      "path": "/seam_maps/draft-version",
      "fields": [
        {
          "name": "code",
          "label": "版本号",
          "kind": "text",
          "initial": "KNN-K8"
        },
        {
          "name": "neighbors",
          "label": "近邻数",
          "kind": "int",
          "initial": 8
        }
      ],
      "help": "试算版本不影响出单，现役版本照常评分。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "run_trial",
      "label": "发起同批对照试算",
      "path": "/seam_maps/run-trial",
      "fields": [
        {
          "name": "version",
          "label": "试算版本",
          "kind": "text",
          "initial": "KNN-K8"
        }
      ],
      "help": "用同一批带载复检样本对比现用版与试算版；参加复检对照的冰雕不进参考池。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "record_trial",
      "label": "登记试算对照结论",
      "path": "/seam_maps/record-trial",
      "fields": [
        {
          "name": "code",
          "label": "对照编号",
          "kind": "text",
          "initial": "TRY-24"
        },
        {
          "name": "token",
          "label": "计算凭据",
          "kind": "token",
          "initial": ""
        }
      ],
      "help": "把同批对照的漏报和误报计入台账。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "enable_version",
      "label": "启用试算版本",
      "path": "/seam_maps/enable-version",
      "fields": [
        {
          "name": "code",
          "label": "试算版本",
          "kind": "text",
          "initial": "KNN-K8"
        }
      ],
      "help": "漏报不增加且误报减少才可启用；启用后新申请按新版本评分，已排队的照原版算。",
      "roles": [
        "reviewer"
      ],
      "success": "已启用"
    }
  ]
};

        export const {title} = page;
        export const key = "seam_maps";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
