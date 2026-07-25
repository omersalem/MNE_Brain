# Ministry Server Inventory – Complete Reference

## VLAN 71 – Core Application Servers (172.23.71.x)

### Database & Email
| Server | IP | Role |
|---|---|---|
| MNEPDB-SRV | `172.23.71.73` | Primary SQL Database |
| EXCHANGESRV1 | `172.23.71.35` | Primary Email Server |
| EXCHANGESRV2 | `172.23.71.36` | Secondary Email Server |
| report_oracle_srv_new_1 | `172.23.71.60` | Oracle Reporting Server |
| OEM-SRV | `172.23.71.68` | Oracle Enterprise Manager |

### Collaboration & Document Management
| Server | IP | Role |
|---|---|---|
| sharepiont-srv | `172.23.71.149` | SharePoint Document Portal |
| OpenKMweb-srv | `172.23.71.142` | Document Management System |
| Archive-srv | `172.23.71.56` | Primary Archiving Server |
| Departmentarchive-srv | `172.23.71.21` | Department Archiving Server |
| FileSharing-srv | `172.23.71.100` | File Sharing Server |
| FILEPRINTSERVER_New | `172.23.71.23` | File and Print Server |

### Web Services
| Server | IP | Role |
|---|---|---|
| Web_Page_Mne | `172.23.71.66` | Ministry Website Server |
| website-srv | `172.23.71.59` | Ministry Website Server |
| Web_Portal_Srv | `172.23.71.103` | Web Portal Server |

### Infrastructure Services
| Server | IP | Role |
|---|---|---|
| MNE-DC1 | `172.23.71.27` | Primary Domain Controller |
| MNE-DC2 | `172.23.71.28` | Secondary Domain Controller |
| MNE-DHCP | `172.23.71.32` | DHCP Server |
| WSUS-SRV | `172.23.71.80` | Windows Update Server |
| SystemCenter | `172.23.71.84` | System Center Management |

### Security Services
| Server | IP | Role |
|---|---|---|
| TrendMicro-DDI | `172.23.71.81` | Threat Detection |
| Antivirus-srv | `172.23.71.199` | Antivirus Management |
| Sophos Mail Protection | `172.23.71.39` | Email Security |
| MNE-FIleScan-Srv | `172.23.71.171` | File Scanning |
| EDRCore | `172.23.71.130` | Endpoint Detection & Response |
| FAZ-2024 | `172.23.71.206` | FortiAnalyzer |
| FortiManager-VM | `172.23.71.205` | FortiManager |

### Specialized Applications
| Server | IP | Role |
|---|---|---|
| Tools-srv | `172.23.71.111` | IT Tools Server |
| Indust-Dev | `172.23.71.47` | Industrial Development |
| Indust_Prod | `172.23.71.48` | Industrial Production |
| mnep_dr_srv | `172.23.71.75` | Disaster Recovery Server |
| support-srv | `172.23.71.9` | Support Services |
| mdt01 | `172.23.71.72` | Deployment Toolkit |
| Esooq-srv | `172.23.71.146` | e-Sooq Application |
| Company_Service | `172.23.71.83` | Company Services |
| Sql_Web_srv | `172.23.71.87` | SQL Web Interface |
| Witness-SRV | `172.23.71.55` | Cluster Witness Server |
| UXP_adapter_srv2 | `172.23.71.78` | UXP Adapter |
| MYQ_SRV | `172.23.71.71` | Print Management |

---

## VLAN 75 – Database Servers (172.23.75.x)
| Server | IP | Role |
|---|---|---|
| Manus-Srv | `172.23.75.200` | Dedicated Database Server |

---

## VLAN 79 – Public Web / DMZ Servers (172.23.79.x)
| Server | IP | Role |
|---|---|---|
| ESADAD-SRV | `172.23.79.77` | ESADAD Public Portal |
| procedures-srv | `172.23.79.79` | Procedures System |
| ESADADTEST-SRV | `172.23.79.80` | ESADAD Test Server |
| ESADADMTIT-PRODUCTION | `172.23.79.81` | ESADAD Production |
| ESADAD-MIND-SRV | `172.23.79.83` | ESADAD MIND Server |
| ESADADMTIT-TEST | `172.23.79.78` | ESADAD MTIT Test |
| FMC Ultimate Configurator | `172.23.79.100` | FMC Configurator |

---

## VLAN 30 – Development & Testing (172.23.30.x)
| Server | IP | Role |
|---|---|---|
| DEV_ABRS | `172.23.30.102` | Development Server |
| Staging_ABRS | `172.23.30.100` | Staging Server |
| UAT_ABRS | `172.23.30.101` | UAT Server |
| Automation_ABRS | `172.23.30.105` | Automation Server |

---

## VLAN 69 – VMware Management (172.23.69.x)
| Server | IP | Role |
|---|---|---|
| VMware vCenter Server 7.3j | `172.23.69.38` | vCenter |
| Veeam Proxy | `172.23.69.71` | Backup Proxy |
| vCenter FTP Backup Server | `172.23.69.110` | Backup Storage |

---

## VLAN 74 – ERCompany (172.23.74.x)
| Server | IP | Role |
|---|---|---|
| Company_reg_App | `172.23.74.10` | Company Registration Application |
| Company_reg_DB | `172.23.74.12` | Company Registration Database |

---

## VLAN 72 – Trade (172.23.72.x)
| Server | IP | Role |
|---|---|---|
| trade-srv2 | `172.23.72.2` | Trade Server |
| wipo-publish | `172.23.72.54` | WIPO Publishing |
| Hasasneh_New_Server | `172.23.72.100` | Hasasneh Server |
| sp2010-srv.mne.gov | `172.23.72.114` | SharePoint 2010 |
| sp2017-srv | `172.23.72.210` | SharePoint 2017 |
| sp2018-srv | `172.23.72.212` | SharePoint 2018 |

---

## VLAN 78 – Application (172.23.78.x)
| Server | IP | Role |
|---|---|---|
| Apex-srv | `172.23.78.50` | Apex Application Server |
| Ticket-srv | `172.23.78.150` | Ticketing Server |

---

## VLAN 55 – MIND UXP (172.23.55.x)
| Server | IP | Role |
|---|---|---|
| mind_uxp_adapter | `172.23.55.55` | MIND UXP Adapter |
| mind_uxp_portal | `172.23.55.60` | MIND UXP Portal |
| mind_uxp_Security | `172.23.55.70` | MIND UXP Security |
| mind_uxp_Connector | `172.23.55.80` | MIND UXP Connector |

---

## VLAN 81 – HR Clock (172.23.81.x)
| Server | IP | Role |
|---|---|---|
| HR_SRV | `172.23.81.72` | HR Server |

---

## VLAN 88 – UXP (172.23.88.x)
| Server | IP | Role |
|---|---|---|
| UXP Security Server | `172.23.88.20` | UXP Security |
| uxp_portal server | `172.23.88.30` | UXP Portal |
| uxp connector server | `172.23.88.40` | UXP Connector |
| egovadapter-srv1 | `172.23.88.215` | eGov Adapter |

---

## VLAN 70 – Network Device Management (172.23.70.x)
| Device | IP | Role |
|---|---|---|
| Cisco_Secure_FW_Mgmt_Center | `172.23.70.77` | Cisco FMC |
| Cisco FTD | `172.23.70.78` | Server-side Firewall |
| F5 WAF | `172.23.70.89` | Web Application Firewall |
| Cisco CoreSwitch1 | `172.23.70.254` | Campus Aggregation |
| Fujitsu Core (MNE-CoreSw2) | `172.23.70.71` | Core Fabric Switch |
