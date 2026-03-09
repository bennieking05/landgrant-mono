# State Requirements Map

This document visualizes how the 50 states group by key eminent domain requirements.

## Overview Diagram

```mermaid
flowchart TB
    subgraph Compensation [Compensation Enhancements]
        subgraph MultiplierStates [Residence/Heritage Multipliers]
            MI["MI: 125% residence"]
            MO["MO: 150% family 50yr<br/>125% homestead"]
            LA["LA: 125% residence"]
        end
        
        subgraph GoodwillStates [Business Goodwill]
            CA["CA: Goodwill compensable"]
            NV["NV: Goodwill in some cases"]
        end
        
        subgraph FullCompStates [Full Compensation Standard]
            FL["FL: Constitutional<br/>full compensation"]
        end
        
        subgraph LostProfitsStates [Lost Profits/Access]
            VA["VA: Lost profits 3yr<br/>+ lost access"]
        end
    end
    
    subgraph AttorneyFees [Attorney Fee Rules]
        subgraph AutoFees [Automatic/Mandatory]
            FL2["FL: Automatic all fees"]
            MI2["MI: Mandatory reimbursement"]
        end
        
        subgraph ThresholdFees [Threshold-Based]
            TX2["TX: If condemnor fails procedure"]
            IN2["IN: If award exceeds appraisers"]
            MO2["MO: If award exceeds 20%"]
            CA2["CA: Reasonableness test"]
            AZ["AZ: If award exceeds 20%"]
            OR["OR: If exceeds 30%"]
        end
        
        subgraph NoFees [No Fee Recovery]
            AL["AL: No reimbursement"]
            NY2["NY: Only if substantially exceeds"]
        end
    end
```

## Post-Kelo Reform Classification

```mermaid
flowchart LR
    subgraph StrongReform [Strong Protections - Constitutional]
        MI3["Michigan 2006"]
        FL3["Florida 2006"]
        VA3["Virginia 2012"]
        TX3["Texas 2009"]
        NV3["Nevada 2006/2008"]
        ND["North Dakota 2006"]
        SC["South Carolina 2006"]
        NH["New Hampshire 2006"]
        GA["Georgia 2006"]
    end
    
    subgraph ModerateReform [Moderate - Statutory Only]
        IN3["Indiana 2006"]
        MO3["Missouri 2006"]
        OH["Ohio 2006"]
        IL["Illinois 2006"]
        MN["Minnesota 2006"]
        WI["Wisconsin 2006"]
        KS["Kansas 2006"]
        TN["Tennessee 2006"]
        KY["Kentucky 2006"]
        WV["West Virginia 2006"]
        ID["Idaho 2006"]
        MT["Montana 2007"]
        WY["Wyoming 2007"]
        UT["Utah 2007"]
        NM["New Mexico 2007"]
        SD["South Dakota 2006"]
        NE["Nebraska 2006"]
        IA["Iowa 2006"]
        CO["Colorado 2006"]
        WA["Washington 2007"]
        OR3["Oregon 2006"]
        AZ3["Arizona 2006"]
        DE["Delaware 2005"]
        AR["Arkansas 2007"]
        OK["Oklahoma 2006"]
    end
    
    subgraph LimitedReform [Limited/No Reform]
        CA3["California 2008<br/>Prop 99 homes only"]
        NY3["New York<br/>No new limits"]
        MA["Massachusetts<br/>No new limits"]
        MD["Maryland<br/>Cosmetic only"]
        NJ["New Jersey<br/>Blight tightened"]
        CT["Connecticut 2007<br/>Primary purpose test"]
        RI["Rhode Island<br/>No statutory change"]
        HI["Hawaii<br/>No change"]
        AK["Alaska<br/>No change"]
        VT["Vermont<br/>No statutory change"]
    end
    
    StrongReform --> ModerateReform --> LimitedReform
```

## Blight Standards

```mermaid
flowchart TB
    subgraph BlightProhibited [Blight Takings Prohibited for Private]
        FL4["Florida"]
    end
    
    subgraph ClearConvincing [Clear and Convincing Evidence]
        MI4["Michigan"]
        NV4["Nevada"]
        IL4["Illinois"]
        CO4["Colorado"]
    end
    
    subgraph ParcelSpecific [Parcel-by-Parcel Required]
        MI5["Michigan"]
        MN4["Minnesota"]
        IN4["Indiana"]
        CO5["Colorado"]
        GA4["Georgia"]
    end
    
    subgraph BlightAllowed [Blight Allowed with Restrictions]
        TX4["Texas: Restricted"]
        CA4["California: Required"]
        PA["Pennsylvania: Required"]
        NJ4["New Jersey: Tightened"]
        NY4["New York: Still allowed"]
        MA4["Massachusetts: Decadent area"]
    end
    
    BlightProhibited --> ClearConvincing --> ParcelSpecific --> BlightAllowed
```

## Quick-Take Availability

```mermaid
flowchart LR
    subgraph QuickTakeYes [Quick-Take Available]
        subgraph DepositPossession [Deposit and Possession]
            TX5["Texas"]
            MI6["Michigan"]
            MO5["Missouri"]
            IN5["Indiana"]
            CA5["California"]
        end
        
        subgraph OrderTaking [Order of Taking]
            FL5["Florida - Ch 74"]
            GA5["Georgia"]
            SC5["South Carolina"]
        end
        
        subgraph DeclarationTaking [Declaration of Taking]
            PA5["Pennsylvania"]
            NJ5["New Jersey"]
            MD5["Maryland"]
        end
        
        subgraph CertificateTake [Certificate of Take]
            VA5["Virginia"]
        end
    end
    
    subgraph QuickTakeLimited [Limited/Restricted]
        KS5["Kansas: Highway only"]
        WV5["West Virginia: Bond required"]
        KY5["Kentucky: Highways 20 days"]
    end
    
    subgraph QuickTakeNo [No Quick-Take]
        NoteNo["Several states require<br/>full process before possession"]
    end
```

## Notice Period Requirements

```mermaid
flowchart TB
    subgraph LongNotice [60+ Days Notice]
        MO6["Missouri: 60 day intent"]
        IA5["Iowa: 90 day for ag land"]
    end
    
    subgraph StandardNotice [30 Days Notice]
        TX6["Texas: 30 initial + 14 final"]
        IN6["Indiana: 30 days"]
        FL6["Florida: 30 days Order of Taking"]
        MI7["Michigan: 45 days with appraisal"]
        OH5["Ohio: 30 days"]
        SC6["South Carolina: 30 days"]
        WY5["Wyoming: 30 days"]
    end
    
    subgraph ShortNotice [Under 30 Days]
        CA6["California: 15-20 days hearing"]
        NY5["New York: 30 day challenge window"]
        MD6["Maryland: 7-10 days quick-take"]
    end
    
    subgraph BillOfRights [Landowner Bill of Rights Required]
        TX7["Texas: 7 days before final"]
        FL7["Florida: Written disclosure"]
    end
```

## Trial/Compensation Determination Method

```mermaid
flowchart TB
    subgraph JuryTrial [Jury Trial Available]
        Most["Most States<br/>TX, FL, MI, IN, CA, etc."]
    end
    
    subgraph Commissioners [Commissioners/Appraisers Panel]
        subgraph ThreeComm [Three Commissioners]
            TX8["Texas: Special commissioners"]
            IN7["Indiana: Court-appointed appraisers"]
            MO7["Missouri: Three commissioners"]
            OH6["Ohio: Commissioners"]
        end
        
        subgraph BoardView [Board of View]
            PA6["Pennsylvania: Board of View"]
        end
        
        subgraph JuryView [Jury of View]
            TN5["Tennessee: Jury of view"]
        end
    end
    
    subgraph BenchTrial [Bench Trial/No Jury]
        MA5["Massachusetts: Judge decides"]
        CT5["Connecticut: Judge/referee"]
    end
    
    JuryTrial --> Commissioners --> BenchTrial
```

## State Groupings Summary Table

| Category | States | Key Characteristic |
|----------|--------|-------------------|
| **Enhanced Compensation** | MI, MO, LA, VA | Multipliers or additional damages |
| **Business Goodwill** | CA, (NV partial) | Compensate lost goodwill |
| **Full Compensation** | FL | Constitutional "full" not "just" |
| **Automatic Atty Fees** | FL, MI | Condemnor always pays fees |
| **Strongest Post-Kelo** | FL, MI, VA, TX, NV, ND | Constitutional ban on econ dev |
| **No Reform** | NY, MA, MD, RI, HI, AK, VT | Still allow broad takings |
| **Blight Prohibited** | FL | Cannot use blight for private |
| **Clear/Convincing Blight** | MI, NV, IL, CO | Higher proof standard |
| **Bill of Rights Required** | TX, FL | Written disclosure to owner |
| **Long Notice (60+ days)** | MO, IA | Extended negotiation period |
| **Quick-Take Available** | Most states | Varies by type |
| **Bench Trial Only** | MA, CT | No jury on compensation |

## Regional Patterns

```mermaid
flowchart TB
    subgraph Northeast [Northeast]
        NE_Strong["Strong Procedures<br/>NY, NJ, PA, CT"]
        NE_Weak["Weaker Reforms<br/>NY, MA, RI still allow<br/>broad takings"]
    end
    
    subgraph Midwest [Midwest]
        MW_Comp["Enhanced Compensation<br/>MI: 125%, MO: 150%/125%"]
        MW_Reform["Strong Reforms<br/>OH, IN, MN, WI, IL"]
    end
    
    subgraph South [South]
        S_Strong["Strongest Protections<br/>FL, TX, VA, GA, SC"]
        S_Comp["Full Compensation<br/>FL, VA lost profits"]
        S_BillRights["Bill of Rights<br/>TX, FL"]
    end
    
    subgraph West [West]
        W_Goodwill["Business Goodwill<br/>CA"]
        W_Const["Constitutional Reform<br/>NV, AZ, OR"]
        W_Limited["Limited Reform<br/>CA Prop 99 homes only"]
    end
```

## Implementation Priority Matrix

Based on unique requirements complexity:

| Priority | State | Unique Features to Implement |
|----------|-------|------------------------------|
| 1 | TX | Bill of Rights, detailed timeline, special commissioners |
| 1 | IN | 5 deadline chains, payment elections, extension rules |
| 1 | FL | Full compensation, auto fees, blight prohibition |
| 1 | CA | Resolution of Necessity, business goodwill, Prop 99 |
| 1 | MI | 125% multiplier, mandatory fees, going concern |
| 1 | MO | Heritage bonuses, 60-day notice, citizens appeal |
| 2 | VA | Lost profits/access compensation |
| 2 | NV | PISTOL amendment, strict public use |
| 2 | OH | Norwood decision implications |
| 3 | Others | Standard framework with state-specific citations |
